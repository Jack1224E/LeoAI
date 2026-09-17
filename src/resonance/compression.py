"""
R2F Module 5 — PCA Compression & State Management (Layer 6)
============================================================
Runs PCA on the interference matrices or TF-IDF features to extract
atomic insights and compresses the state to a lightweight JSON file.
"""

import json
from pathlib import Path
from typing import List
import numpy as np
from sklearn.decomposition import PCA

from src.resonance.manifold import ConceptualEmbedding
from src.resonance.solvers import Projection
from src.config import STATE_DIR


def compress_and_save_state(
    problem: str,
    iteration: int,
    embedding: ConceptualEmbedding,
    projections: List[Projection],
    interference_matrix: np.ndarray,
    psi_dom: np.ndarray,
    E_dom: float,
) -> Path:
    """Run PCA to extract atomic insight vectors and serialize state."""
    
    # We apply PCA directly to the interference matrix itself to find
    # the principal components of the *relationships* between perspectives.
    # We only want 2 or 3 components at most.
    n_components = min(3, len(projections))
    
    try:
        pca = PCA(n_components=n_components)
        pca.fit(interference_matrix)
        variance_ratio = pca.explained_variance_ratio_.tolist()
        components = pca.components_.tolist()
    except Exception as e:
        variance_ratio = []
        components = []

    state = {
        "problem": problem,
        "iteration": iteration,
        "embedding": embedding.to_dict(),
        "E_dom": float(E_dom),
        "dominant_eigenvector": psi_dom.tolist(),
        "pca_variance_ratio": variance_ratio,
        "pca_components": components,
        "perspective_weights": {
            p.perspective: float(psi_dom[i]) for i, p in enumerate(projections)
        }
    }

    path = STATE_DIR / "eigen_summary.json"
    path.write_text(json.dumps(state, indent=2))
    return path
