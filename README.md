# LeoAI (Resonant Reasoning Field)

LeoAI is a non-sequential, continuous-manifold reasoning framework for large language models, drawing inspiration from quantum mechanics and physical wave interference rather than traditional Task Graphs or DAGs.

## Architecture & Modules

### Module 1: Manifold Embedder
- **Jargon:** Generates a 4D conceptual embedding (Domain, Transformation, Constraints, Info Gradient) from the raw problem and maps orthogonal perspective directives.
- **Real-Life Analogy:** Think of this as the "Mission Briefing." Instead of just telling 5 experts to "solve the problem," the embedder defines the exact battlefield terrain, rules of engagement, and assigns each expert a hyper-specific, non-overlapping angle to attack from (e.g., the Builder, the Saboteur, the Analyst).

### Module 2: Parallel Eigen-Solvers
- **Jargon:** Spawns $K$ parallel, strictly isolated LLM instances that project the embedding through their assigned perspective vectors via asyncio multiplexing.
- **Real-Life Analogy:** Imagine putting 5 experts in 5 separate, soundproof rooms. They all get the same mission briefing, but they are forbidden from talking to each other. They each write a report strictly through their own lens.

### Module 3: Interference Engine
- **Jargon:** Computes a $K \times K$ interference matrix (cosine similarity of TF-IDF vectors) between the solvers. Extracts eigenvalues and eigenvectors via `numpy.linalg.eigh` to find the dominant consensus state $|\Psi\rangle$.
- **Real-Life Analogy:** Throwing all 5 reports into a blender to measure how much they overlap and clash. The "dominant eigenstate" is the resulting summary that perfectly balances the strongest, most stable arguments from the group, weighted by how well they resonate with each other.

### Module 4: Recurrence, Tunneling, and Reinjection
- **Jargon:** Reinjects the dominant eigenstate back into the parallel solvers. If the stability metric $E$ falls into a local minimum ($0.5 < E < 0.8$), it triggers Quantum Tunneling (semantic noise injection) to force a state shift.
- **Real-Life Analogy:** We take the blended summary, slide it under the door of the 5 soundproof rooms, and ask the experts to refine their arguments based on the group's current consensus. If the consensus is boring or "stuck" (Quantum Tunneling), we slide in a radical, chaotic idea to violently shake up their thinking.

### Module 5: PCA Compression
- **Jargon:** Applies Principal Component Analysis (PCA) to the interference matrix to extract atomic insights and compress the tensor state to a lightweight, serializable JSON format.
- **Real-Life Analogy:** Distilling a 500-page debate transcript into a 1-page executive summary bullet-point list that only captures the absolute core disagreements and breakthroughs, making it easy to store and read later.
