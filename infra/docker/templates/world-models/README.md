# World Models for Reinforcement Learning

Template for model-based RL using world models (Dreamer v3, RSSM).

## What Are World Models?

World models learn a **representation of the environment** to enable:
- Planning in learned latent space
- Sample-efficient RL (100x less data)
- Offline RL and sim-to-real transfer

### Key Approaches
1. **Dreamer v3** - SOTA world model (2023)
2. **RSSM** - Recurrent State Space Model
3. **Model-Based RL** - Plan using learned dynamics

## Quick Start

```bash
# Train world model
python train.py --env CartPole-v1 --episodes 1000

# Evaluate
python evaluate.py --checkpoint models/best.pt
```

## Use Cases
- Robotics (sim-to-real)
- Game AI (Atari, MuJoCo)
- Autonomous systems
- Sample-efficient RL

## Resources
- Dreamer v3: https://danijar.com/project/dreamerv3/
- Paper: https://arxiv.org/abs/2301.04104

**Created:** November 15, 2025  
**Status:** Production-Ready
