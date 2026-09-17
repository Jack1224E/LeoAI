"""
R2F Main CLI Harness
====================
Takes a problem string, spins up the K perspectives, runs the recurrence
loop until E converges or max_iterations is hit, and outputs the
final collapsed eigenstate.
"""

import asyncio
import sys
import time

from src.proxy.session_manager import SessionManager
from src.resonance.manifold import embed_problem, generate_perspectives, save_embedding
from src.resonance.solvers import solve_all, _solve_one
from src.resonance.interference import InterferenceEngine, format_dominant_state
from src.resonance.compression import compress_and_save_state
from src.resonance.recurrence import generate_reinjection_prompt


async def run_r2f_harness(problem: str, max_iterations: int = 3):
    print("==================================================")
    print("  R2F (Resonant Reasoning Field) Harness Started")
    print("==================================================\n")
    
    mgr = SessionManager(model_alias="primary")
    interference_engine = InterferenceEngine()

    # Module 1: Manifold Embedder
    print("[Module 1] Generating Conceptual Embedding (ψ₀)...")
    emb = await embed_problem(problem, mgr)
    perspectives = generate_perspectives(emb, k=5)
    save_embedding(emb, perspectives, problem)
    print(f"  -> Domain: {emb.domain}")
    print(f"  -> {len(perspectives)} perspectives initialized.\n")

    # Module 2: Initial Parallel Solve
    print("[Module 2] Spawning Parallel Eigen-Solvers...")
    projections = await solve_all(problem, emb, perspectives, mgr, timeout=90)
    print(f"  -> {len(projections)} projections received.\n")

    E_prev = 0.0

    # Recurrence Loop
    for iteration in range(max_iterations):
        print(f"--- ITERATION {iteration} ---")
        
        # Module 3: Superposition & Interference
        I, evals, E_dom, psi_dom = interference_engine.compute_interference(projections)
        print(f"  -> Dominant Eigenvalue (E): {E_dom:.4f}")
        
        # Module 5: PCA Compression & State Management
        compress_and_save_state(problem, iteration, emb, projections, I, psi_dom, E_dom)
        print(f"  -> State serialized to .state/eigen_summary.json")

        dominant_state_str = format_dominant_state(projections, psi_dom)

        # Convergence Check
        delta_E = abs(E_dom - E_prev)
        print(f"  -> ΔE = {delta_E:.4f}")
        
        if E_dom > 0.9 and delta_E < 0.01:
            print("\n*** CONVERGENCE ACHIEVED ***")
            break
            
        if iteration == max_iterations - 1:
            print("\n*** MAX ITERATIONS REACHED ***")
            break

        E_prev = E_dom

        # Module 4: Reinjection & Tunneling
        print("  -> Reinjecting dominant state to solvers...")
        tasks = []
        for p in perspectives:
            prompt = generate_reinjection_prompt(
                problem=problem,
                perspective_name=p.name,
                dominant_state_str=dominant_state_str,
                E_dom=E_dom,
                iteration=iteration,
            )
            # Submit reinjection directly via proxy
            tasks.append(mgr.submit(prompt, timeout=90))
        
        # Wait for reinjected responses
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update projections with new data
        for i, res in enumerate(results):
            if not isinstance(res, Exception):
                # Simple parsing fallback for iterative loop (usually we'd use _solve_one's full parser)
                projections[i].projection = res.response
                projections[i].insight_novelty = "Refined in iteration " + str(iteration)
                projections[i].raw_response = res.response
        print()

    print("\n==================================================")
    print("  R2F Harness Finished.")
    print("==================================================")
    print(f"Final State: E = {E_dom:.4f}")
    print("\nFinal Dominant Eigenstate:\n")
    print(dominant_state_str)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.main \"<problem_statement>\"")
        sys.exit(1)
        
    problem = sys.argv[1]
    asyncio.run(run_r2f_harness(problem))
