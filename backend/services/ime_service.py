"""
Service: Check adverse reactions against EMA IME (Important Medical Events) list.
Uses semantic similarity (sentence-transformers) to match free-text reactions
against MedDRA preferred terms in the IME CSV.
"""

from __future__ import annotations
import logging
import time
import pandas as pd
import numpy as np
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from core.llm_client import LLMClient
from models.schemas import IMEAssessment, IMEMatch
from models.schemas import IME_SCHEMA

logger = logging.getLogger(__name__)

# EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# EMBEDDING_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
SIMILARITY_THRESHOLD = 0.50  # minimum cosine similarity to consider a match


class _ReactionExtractionItem(BaseModel):
    reaction_ru: str = Field(..., description="Нежелательная реакция в оригинальном тексте")
    reaction_en: str = Field(..., description="Перевод реакции на английский для поиска")


class _ReactionExtractionOutput(BaseModel):
    reactions: list[_ReactionExtractionItem] = Field(
        default_factory=list,
        description="Список нежелательных реакций с переводом"
    )


EXTRACTION_SYSTEM = """Ты — медицинский кодировщик MedDRA. Извлеки из текста
все упомянутые нежелательные реакции/побочные эффекты.
Верни JSON с полем "reactions", где каждая реакция содержит:
  - reaction_ru: текст реакции на русском языке, точно как в кейсе
  - reaction_en: корректный перевод этой реакции на английский язык
Используй краткие медицинские термины.
Отвечай строго в формате JSON."""


class IMEService:
    def __init__(self, llm: LLMClient, ime_csv_path: Optional[str] = None):
        self.llm = llm
        self._embedder = None
        self._ime_df: Optional[pd.DataFrame] = None
        self._ime_vectors: Optional[np.ndarray] = None
        self._good_list: list[str] = []
        self._good_vectors: Optional[np.ndarray] = None

        default_path = Path(__file__).parent.parent / "data" / "ema_ime_list.csv"
        path = Path(ime_csv_path) if ime_csv_path else default_path
        if path.exists():
            self._load_ime(path)
        else:
            logger.warning("EMA IME list not found at %s. IME check disabled.", path)

        try:
            self._load_good_list(Path(__file__).parent.parent / "data" / "good_list.txt")
        except Exception as e:
            logger.warning("Failed to load safe reaction list: %s", e)

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedder

    def _load_ime(self, path: Path):
        df = pd.read_csv(path, sep=';')
        # Normalize column names (handle BOM, spaces, etc.)
        df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
        # Expected columns: MedDRA, PT Name, SOC Name  (flexible matching)
        col_map = {}
        for col in df.columns:
            cl = col.lower().replace(" ", "_")
            if "pt" in cl and "name" in cl:
                col_map["pt_name"] = col
            elif "soc" in cl:
                col_map["soc_name"] = col
            elif "meddra" in cl or cl in ("code", "meddra_code"):
                col_map["meddra"] = col
        if "pt_name" not in col_map:
            raise ValueError(f"Cannot find PT Name column in {path}. Columns: {list(df.columns)}")
        self._ime_df = df
        self._col_map = col_map

        # Try to load cached embeddings first
        cache_file = path.parent / f"{path.stem}_embeddings.npy"
        pt_names = df[col_map["pt_name"]].fillna("").tolist()
        
        if cache_file.exists():
            try:
                self._ime_vectors = np.load(cache_file)
                logger.info("IME embeddings loaded from cache: %s", cache_file)
                self._pt_names = pt_names
                return
            except Exception as e:
                logger.warning("Failed to load cached IME embeddings: %s. Recomputing...", e)
        
        # Pre-compute embeddings for all PT Names
        embedder = self._get_embedder()
        self._ime_vectors = embedder.encode(
            pt_names, normalize_embeddings=True, show_progress_bar=False
        )
        self._pt_names = pt_names
        
        # Save embeddings to cache
        try:
            np.save(cache_file, self._ime_vectors)
            logger.info("IME embeddings cached to: %s", cache_file)
        except Exception as e:
            logger.warning("Failed to cache IME embeddings: %s", e)
        
        logger.info("IME list loaded: %d terms", len(pt_names))

    def _load_good_list(self, path: Path):
        try:
            if not path.exists():
                logger.info("Safe reaction list not found at %s. Skipping safe filtering.", path)
                return
            with path.open("r", encoding="utf-8") as f:
                self._good_list = [line.strip() for line in f if line.strip()]
            if not self._good_list:
                logger.info("Safe reaction list is empty at %s.", path)
                return
            
            # Try to load cached embeddings first
            cache_file = path.parent / f"{path.stem}_embeddings.npy"
            if cache_file.exists():
                try:
                    self._good_vectors = np.load(cache_file)
                    logger.info("Safe-list embeddings loaded from cache: %s", cache_file)
                    return
                except Exception as e:
                    logger.warning("Failed to load cached safe-list embeddings: %s. Recomputing...", e)
            
            embedder = self._get_embedder()
            self._good_vectors = embedder.encode(
                self._good_list, normalize_embeddings=True, show_progress_bar=False
            )
            
            # Save embeddings to cache
            try:
                np.save(cache_file, self._good_vectors)
                logger.info("Safe-list embeddings cached to: %s", cache_file)
            except Exception as e:
                logger.warning("Failed to cache safe-list embeddings: %s", e)
            
            logger.info("Safe reaction list loaded: %d terms", len(self._good_list))
        except Exception as e:
            logger.error("Error loading safe reaction list from %s: %s", path, e)
            self._good_list = []
            self._good_vectors = None

    @property
    def is_available(self) -> bool:
        return self._ime_df is not None

    def _extract_reactions(self, case_text: str) -> list[_ReactionExtractionItem]:
        try:
            result: _ReactionExtractionOutput = self.llm.complete_structured(
                system_prompt=EXTRACTION_SYSTEM,
                user_prompt=f"Извлеки нежелательные реакции из:\n\n{case_text}",
                schema=_ReactionExtractionOutput,
                schema_hint_explicit=IME_SCHEMA
            )
            logger.debug("LLM extraction result: %s", result)
            if not isinstance(result, dict):
                logger.error("LLM returned non-dict result: %s (type: %s)", result, type(result))
                return []
            if "reactions" not in result:
                logger.warning("LLM result missing 'reactions' key. Keys present: %s", list(result.keys()))
                return []
            reactions = _ReactionExtractionOutput.model_validate(result)
            logger.debug("CASE EXTRACTOR RAW: %s", reactions.reactions)
            return reactions.reactions
        except Exception as e:
            logger.error("Error in reaction extraction: %s", e, exc_info=True)
            return []

    def _find_ime_matches(self, reaction_item: _ReactionExtractionItem) -> tuple[list[IMEMatch], dict]:
        """
        Returns IME matches AND debug info about good_list matches for Judge.
        Returns (matches, debug_info) where debug_info contains good_list comparison.
        """
        if self._ime_vectors is None or self._ime_df is None:
            return [], {}

        embedder = self._get_embedder()
        search_text = reaction_item.reaction_en.strip() or reaction_item.reaction_ru
        logger.info("[IME] Encoding query: %r  (model=%s)", search_text, EMBEDDING_MODEL)
        t0 = time.perf_counter()
        qvec = embedder.encode([search_text], normalize_embeddings=True, show_progress_bar=False)
        logger.info("[IME] Embedding done in %.1fs", time.perf_counter() - t0)
        scores = (self._ime_vectors @ qvec.T).flatten()
        best_indices = np.argsort(scores)[::-1][:3]

        matches = []
        best_ime_score = 0.0
        
        # Log top IME matches
        logger.info("=== IME MATCHING FOR: %s ===", search_text)
        ime_top_matches = []
        for idx in best_indices:
            score = float(scores[idx])
            row = self._ime_df.iloc[idx]
            pt_col = self._col_map["pt_name"]
            pt_name = str(row[pt_col])
            ime_top_matches.append((pt_name, score))
            
            if score >= SIMILARITY_THRESHOLD:
                best_ime_score = max(best_ime_score, score)
                soc_col = self._col_map.get("soc_name", pt_col)
                meddra_col = self._col_map.get("meddra")
                matches.append(IMEMatch(
                    reaction_from_text=reaction_item.reaction_ru,
                    ime_pt_name=pt_name,
                    ime_soc_name=str(row[soc_col]) if soc_col in row.index else "",
                    meddra_code=str(row[meddra_col]) if meddra_col and meddra_col in row.index else None,
                    similarity_score=round(score, 3),
                ))
        
        logger.info("Top IME matches: %s", ime_top_matches)
        logger.info("Best IME score above threshold (%.2f): %.3f, matches found: %d", SIMILARITY_THRESHOLD, best_ime_score, len(matches))

        debug_info = {
            "best_ime_score": best_ime_score,
            "ime_top_matches": ime_top_matches,
        }

        # Check good_list for comparison
        if self._good_vectors is not None and len(self._good_vectors) > 0:
            good_scores = (self._good_vectors @ qvec.T).flatten()
            best_good_indices = np.argsort(good_scores)[::-1][:3]
            best_good_score = float(np.max(good_scores))
            
            good_top_matches = []
            for idx in best_good_indices:
                score = float(good_scores[idx])
                good_term = self._good_list[idx]
                good_top_matches.append((good_term, score))
            
            logger.info("Top safe-list matches: %s", good_top_matches)
            logger.info("Best safe-list score: %.3f", best_good_score)
            logger.info("COMPARISON: Best IME=%.3f vs Best safe-list=%.3f", best_ime_score, best_good_score)
            
            debug_info["best_good_score"] = best_good_score
            debug_info["good_top_matches"] = good_top_matches

        return matches, debug_info

    def _judge_ime_candidates(self, reaction_item: _ReactionExtractionItem, case_text: str, matches: list[IMEMatch], debug_info: dict) -> list[IMEMatch]:
        """
        Apply LLM-as-a-Judge to filter out false positive IME matches.
        Judges have access to both IME candidates AND safe-list (good_list) candidates.
        Returns only matches that are confirmed by the judge as genuinely clinically significant.
        """
        if not matches:
            return []
        
        # Prepare candidate list for the judge
        candidates_text = "\n".join([f"- {match.ime_pt_name} (SOC: {match.ime_soc_name}, similarity: {match.similarity_score})" for match in matches])
        
        # Add good_list comparison info to judge prompt
        safe_list_info = ""
        if "good_top_matches" in debug_info:
            good_matches = debug_info["good_top_matches"]
            good_score = debug_info.get("best_good_score", 0.0)
            ime_score = debug_info.get("best_ime_score", 0.0)
            safe_list_info = (
                f"\n\nCРАВНЕНИЕ С БЕЗОПАСНЫМИ РЕАКЦИЯМИ (not IME):\n"
                f"Top безопасные реакции: {good_matches}\n"
                f"Наилучший score из безопасного списка: {good_score:.3f}\n"
                f"Наилучший score из IME списка: {ime_score:.3f}\n"
                f"Вывод: Если безопасный score > IME score, это скорее всего НЕ IME событие.\n"
            )
        
        judge_system = (
            "Ты — эксперт по фармаконадзору и медицинской классификации IME (Important Medical Events). "
            "Твоя задача — проверить, является ли данная нежелательная реакция действительно КЛИНИЧЕСКИ ЗНАЧИМЫМ событием IME. "
            "У тебя есть информация о том, найдена ли эта реакция в IME списке И в списке безопасных (не-IME) реакций. "
            "Если реакция找в безопасном списке с более высоким сходством — это НЕ IME. "
            "Отвечай только 'YES' (событие действительно важно для IME) или 'NO' (это не IME). "
            "Не пиши никакого дополнительного текста, только YES или NO."
        )
        
        judge_user = (
            f"Контекст кейса: {case_text[:500]}\n\n"
            f"Извлеченная реакция (русский): {reaction_item.reaction_ru}\n"
            f"Извлеченная реакция (английский): {reaction_item.reaction_en}\n\n"
            f"Найденные IME кандидаты:\n{candidates_text}"
            f"{safe_list_info}\n"
            f"Вопрос: Является ли эта реакция действительно клинически значимым IME событием? "
            f"Учитывай: тяжесть, необходимость госпитализации, угрозу для жизни. "
            f"Если реакция в безопасном списке с лучшим score — ответь NO. "
            f"Отвечай только YES или NO."
        )
        
        try:
            logger.info("[IME] Judge LLM call for: %r", reaction_item.reaction_en)
            t0 = time.perf_counter()
            raw_response = self.llm.complete_text(judge_system, judge_user)
            logger.info("[IME] Judge LLM done in %.1fs", time.perf_counter() - t0)
            decision = raw_response.strip().upper()

            if "YES" in decision:
                logger.info("[IME] Judge APPROVED matches for: %s", reaction_item.reaction_en)
                return matches
            else:
                logger.info("[IME] Judge REJECTED matches for: %s (response: %s)", reaction_item.reaction_en, decision)
                return []
        except Exception as e:
            logger.warning("[IME] Judge evaluation failed for %s: %s. Accepting matches by default.", reaction_item.reaction_en, e)
            return matches

    def assess(self, case_text: str) -> IMEAssessment:
        t_start = time.perf_counter()
        logger.info("[IME] Step 2 started. Model: %s", EMBEDDING_MODEL)

        logger.info("[IME] Extracting reactions via LLM...")
        t0 = time.perf_counter()
        reaction_items = self._extract_reactions(case_text)
        logger.info("[IME] LLM extraction done in %.1fs — %d reaction(s): %s",
                    time.perf_counter() - t0,
                    len(reaction_items),
                    [r.reaction_en for r in reaction_items])

        extracted_reactions = [item.reaction_ru for item in reaction_items]

        if not self.is_available:
            logger.warning("[IME] IME list not loaded — skipping matching")
            return IMEAssessment(
                is_clinically_significant=False,
                matches=[],
                reactions_not_in_ime=extracted_reactions,
                extracted_reactions=extracted_reactions,
            )

        all_matches: list[IMEMatch] = []
        not_in_ime: list[str] = []

        for i, item in enumerate(reaction_items, 1):
            logger.info("[IME] Processing reaction %d/%d: %r", i, len(reaction_items), item.reaction_en)
            t0 = time.perf_counter()
            matches, debug_info = self._find_ime_matches(item)
            logger.info("[IME] Matching done in %.1fs — %d candidate(s) above threshold",
                        time.perf_counter() - t0, len(matches))

            if matches:
                judged_matches = self._judge_ime_candidates(item, case_text, matches, debug_info)
                if judged_matches:
                    all_matches.extend(judged_matches)
                else:
                    not_in_ime.append(item.reaction_ru)
            else:
                not_in_ime.append(item.reaction_ru)

        logger.info("[IME] Step 2 done in %.1fs total — %d IME match(es)",
                    time.perf_counter() - t_start, len(all_matches))
        return IMEAssessment(
            is_clinically_significant=len(all_matches) > 0,
            matches=all_matches,
            reactions_not_in_ime=not_in_ime,
            extracted_reactions=extracted_reactions,
        )
