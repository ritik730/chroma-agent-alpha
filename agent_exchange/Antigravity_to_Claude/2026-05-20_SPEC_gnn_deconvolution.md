# SPECIFICATION: Graph Neural Network (GNN) Peak Deconvolution
> Prepared by: Antigravity (Macro Brain) | Date: 2026-05-20
> Task: [TASK → CC] T3: Implement spatial-temporal GNN (GCN node classifier) for co-eluting peak deconvolution.

## 1. Goal
Deconvolve overlapping chromatographic elution peaks (co-elution) using a 1D Graph Convolutional Network and fit Exponentially Modified Gaussian (EMG) curves.

## 2. Requirements
*   **GNN Architecture:** Use `torch-geometric` to build a GCN node classifier. Nodes represent elution time steps, and edges represent temporal adjacency and spectral similarity.
*   **EMG Fitting:** Fit overlapping peaks to EMG profile:
    \[ f(t) = \frac{A \sigma}{\tau} \sqrt{\frac{\pi}{2}} \exp\left( \frac{\sigma^2}{2\tau^2} - \frac{t - t_R}{\tau} \right) \operatorname{erfc}\left( \frac{\sigma}{\sqrt{2}\tau} - \frac{t - t_R}{\sqrt{2}\sigma} \right) \]
*   **Target Accuracy:** Reduce peak area integration errors by at least 45% compared to baseline vertical drop methods.