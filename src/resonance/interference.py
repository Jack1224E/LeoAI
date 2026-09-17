"""
R2F Module 3 — Superposition & Interference Engine
===================================================
Takes K partial solutions (Projections) and converts them into an interference
matrix using TF-IDF cosine similarity. Computes eigenvalues/eigenvectors.

The dominant eigenvector |Ψ⟩ represents the consensus state, and its
eigenvalue E represents the stability / natural fitness of the manifold.
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.resonance.solvers import Projection


class InterferenceEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")

    def compute_interference(
        self, projections: List[Projection]
    ) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray]:
        if not projections:
            raise ValueError("No projections provided.")
        
        if len(projections) == 1:
            return np.array([[1.0]]), np.array([1.0]), 1.0, np.array([1.0])

        texts = [f"{p.projection}\n{p.insight_novelty}" for p in projections]

        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
        except ValueError:
            k = len(projections)
            return np.eye(k), np.ones(k), 1.0, np.ones(k) / np.sqrt(k)

        I = cosine_similarity(tfidf_matrix)
        eigenvalues, eigenvectors = np.linalg.eigh(I)
        
        E_dom = eigenvalues[-1]
        psi_dom = eigenvectors[:, -1]

        if np.sum(psi_dom) < 0:
            psi_dom = -psi_dom

        E_dom_normalized = float(E_dom / len(projections))

        return I, eigenvalues, E_dom_normalized, psi_dom


def format_dominant_state(
    projections: List[Projection], psi_dom: np.ndarray
) -> str:
    state_str = "CURRENT DOMINANT EIGENSTATE (|Ψ⟩):\n\n"
    indices = np.argsort(np.abs(psi_dom))[::-1]
    
    for idx in indices:
        p = projections[idx]
        weight = float(psi_dom[idx])
        if abs(weight) < 0.05:
            continue
            
        sign = "+" if weight > 0 else "-"
        state_str += f"[{sign}] PERSPECTIVE: {p.perspective} (Amplitude: {weight:.3f})\n"
        state_str += f"  Insight: {p.insight_novelty}\n"
        state_str += f"  Conflicts: {' | '.join(p.conflict_points)}\n\n"

    return state_str.strip()
