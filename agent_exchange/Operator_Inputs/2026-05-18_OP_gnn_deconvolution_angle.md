# OPERATOR DIRECTION: Peak Deconvolution via GNNs (Research Strategy)
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-05-18
> To: Dual-Agent System (Antigravity & Claude Code)

When compounds exit the chromatography column at similar times, they co-elute, creating overlapping peaks. Standard vertical drop integration methods introduce up to 46.1% to 48.8% area calculation errors. In self-driving laboratories, this measurement noise propagates to reaction yield calculations, causing Bayesian Optimization loops to stall or converge on sub-optimal regimes. 

I want to solve this using a GNN (Graph Neural Network) deconvolution approach.

**My Requirements:**
1. Represent the chromatogram elution profile as a graph (where nodes are time steps, and edges capture adjacency and spectral similarity).
2. Train a Graph Convolutional Network (GCN) node classifier to classify overlapping signals, and fit Exponentially Modified Gaussian (EMG) curves to resolve the individual areas.
3. The GNN must run efficiently on CPU-only hardware (our 16GB RAM laptop) in under 15 seconds.