"""AI/ML — knowledge domain for artificial intelligence and machine learning in robotics."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_ai_ml_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="ai_ml",
        description="AI and Machine Learning for robotics — neural networks, deep learning, reinforcement learning, and intelligent robot behavior.",
        subcategories=["ml_basics", "deep_learning", "reinforcement_learning", "computer_vision_ai", "nlp", "edge_ai", "applications"],
    )

    domain.add_entry(KnowledgeEntry(
        id="ai-ml-basics-001",
        title="Machine Learning Fundamentals for Robotics",
        content="""Machine Learning enables robots to learn from data instead of explicit programming — used for perception, decision-making, and adaptive control.

ML Types:

1. Supervised Learning
   - Input-output pairs: (x, y) — learn mapping from data
   - Tasks: Classification (discrete output), Regression (continuous output)
   - Algorithms: Linear regression, decision trees, SVM, neural networks
   - Robotics: Object recognition, grasp success prediction, anomaly detection

2. Unsupervised Learning
   - Input only: x — find patterns in data
   - Tasks: Clustering, dimensionality reduction, density estimation
   - Algorithms: K-means, DBSCAN, PCA, autoencoders
   - Robotics: Scene segmentation, skill discovery, behavior clustering

3. Reinforcement Learning
   - Agent learns by trial and error in environment
   - Reward signal: +1 for success, -1 for failure
   - Goal: Maximize cumulative reward
   - Robotics: Locomotion, manipulation, navigation, task planning

ML Pipeline:
1. Data collection: Sensors, demonstrations, simulation
2. Preprocessing: Normalize, augment, split (train/val/test)
3. Feature extraction: Raw data → meaningful features (or learn end-to-end)
4. Model training: Optimize parameters to minimize loss
5. Validation: Tune hyperparameters, prevent overfitting
6. Testing: Evaluate on unseen data
7. Deployment: Run model on robot (edge, cloud)

Key Concepts:
- Overfitting: Model memorizes training data, fails on new data
  - Fix: More data, regularization, dropout, early stopping
- Underfitting: Model too simple, can't capture patterns
  - Fix: More complex model, more features, train longer
- Bias-variance tradeoff: Simple (high bias) vs complex (high variance)
- Cross-validation: K-fold to estimate generalization performance

Libraries:
- scikit-learn: Classical ML (regression, SVM, trees, clustering)
- PyTorch: Deep learning (research, flexible)
- TensorFlow/Keras: Deep learning (production, easier deployment)
- Stable-Baselines3: Reinforcement learning (PPO, SAC, TD3)""",
        domain="ai_ml",
        category="ml_basics",
        tags=["ai", "ml", "machine learning", "supervised", "unsupervised"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Classification: CNN for object recognition (input: image, output: class label)",
            "Regression: Neural net for grasp force prediction (input: object features, output: force)",
            "RL: PPO for robot locomotion (input: joint angles, output: motor torques)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ai-deep-learning-001",
        title="Deep Learning and Neural Networks",
        content="""Deep learning uses multi-layer neural networks to learn hierarchical representations — state-of-the-art for perception tasks in robotics.

Neural Network Basics:
- Neuron: weighted sum of inputs + bias → activation function
- Layer: Multiple neurons operating in parallel
- Network: Stacked layers (input → hidden → output)
- Activation functions: ReLU (most common), Sigmoid, Tanh, Softmax (classification)

Common Architectures:

1. Convolutional Neural Networks (CNNs)
   - Convolution layers: Feature extraction (edges, textures, shapes)
   - Pooling layers: Downsample (reduce spatial dimensions)
   - Fully connected layers: Classification
   - Use: Image classification, object detection, segmentation
   - Models: ResNet, EfficientNet, MobileNet (lightweight for edge)

2. Recurrent Neural Networks (RNNs)
   - Process sequences (time series, text)
   - Hidden state maintains memory of past inputs
   - Variants: LSTM (Long Short-Term Memory), GRU (Gated Recurrent Unit)
   - Use: Trajectory prediction, gesture recognition, language models

3. Transformers
   - Self-attention mechanism (weigh importance of different parts)
   - Parallel processing (faster than RNNs)
   - Use: NLP (BERT, GPT), vision (ViT), multimodal (CLIP)
   - Robotics: Task planning, language-conditioned control

Training:
```python
import torch
import torch.nn as nn

# Define model
class RobotPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 64)  # input: 10 features
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, 4)   # output: 4 actions
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

model = RobotPolicy()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
loss_fn = nn.MSELoss()

# Training loop
for epoch in range(100):
    for batch_x, batch_y in dataloader:
        pred = model(batch_x)
        loss = loss_fn(pred, batch_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
```

Deployment on Robot:
- PyTorch: torch.jit.script() for C++ deployment
- ONNX: Cross-platform model format
- TensorRT: NVIDIA GPU optimization (Jetson, desktop)
- TFLite: Mobile/edge deployment (Raspberry Pi, Android)""",
        domain="ai_ml",
        category="deep_learning",
        tags=["ai", "deep learning", "neural network", "cnn", "pytorch"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["ai-ml-basics-001"],
        examples=[
            "CNN: ResNet-18 for object recognition (224x224 image → 1000 classes)",
            "Training: model.train(); loss = criterion(output, target); loss.backward(); optimizer.step()",
            "Deploy: torch.onnx.export(model, dummy_input, 'model.onnx')",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ai-rl-001",
        title="Reinforcement Learning for Robot Control",
        content="""Reinforcement Learning (RL) trains robots through trial and error — learning policies that map observations to actions to maximize reward.

RL Framework:
- Agent: Robot (decision maker)
- Environment: World (physics, objects, constraints)
- State/Observation: Sensor readings (joint angles, camera images)
- Action: Motor commands (torques, velocities)
- Reward: Scalar feedback (+1 success, -1 failure, shaping rewards)
- Policy: Strategy (π(a|s) — probability of action given state)

RL Algorithms:

1. Value-Based (Q-Learning, DQN)
   - Learn value function Q(s,a) — expected return for action in state
   - Policy: Greedy (pick action with highest Q)
   - Use: Discrete actions (game playing, simple control)

2. Policy Gradient (REINFORCE, PPO)
   - Learn policy directly (neural network outputs action probabilities)
   - Optimize: Increase probability of good actions, decrease bad
   - PPO (Proximal Policy Optimization): Stable, sample-efficient, most popular
   - Use: Continuous control (robot arms, locomotion)

3. Actor-Critic (A2C, A3C, SAC, TD3)
   - Actor: Policy (selects actions)
   - Critic: Value function (evaluates actions)
   - SAC (Soft Actor-Critic): Maximum entropy, robust, sample-efficient
   - Use: Complex continuous control, multi-task learning

Training in Simulation:
```python
from stable_baselines3 import PPO
import gymnasium as gym

# Environment (robot in simulation)
env = gym.make('RobotArm-v0')  # custom environment

# Model
model = PPO('MlpPolicy', env, verbose=1, learning_rate=3e-4, n_steps=2048)

# Train
model.learn(total_timesteps=1_000_000)

# Test
obs, _ = env.reset()
for _ in range(1000):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, _ = env.reset()
```

Sim-to-Real Transfer:
- Domain randomization: Vary simulation parameters (friction, mass, delays)
- System identification: Match simulation to real robot
- Fine-tuning: Train in sim, adapt on real robot with small dataset
- Safety: Constrain actions, use safety shields during real-world testing""",
        domain="ai_ml",
        category="reinforcement_learning",
        tags=["ai", "reinforcement learning", "rl", "ppo", "robot control"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["ai-deep-learning-001"],
        examples=[
            "PPO: model = PPO('MlpPolicy', env); model.learn(total_timesteps=1_000_000)",
            "Reward shaping: +100 for reaching target, -1 per step (encourage speed)",
            "Sim-to-real: Randomize friction (0.5-1.5), mass (0.8-1.2), joint delays (0-50ms)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ai-edge-001",
        title="Edge AI — Deploying Models on Robots",
        content="""Edge AI runs inference directly on the robot — low latency, no internet required, privacy-preserving. Essential for real-time robot control.

Edge Hardware:

1. NVIDIA Jetson
   - Jetson Nano: 0.5 TFLOPS, 4GB RAM, $100 (entry-level)
   - Jetson Orin Nano: 40 TOPS, 8GB RAM, $500 (mid-range)
   - Jetson AGX Orin: 275 TOPS, 64GB RAM, $2000 (high-performance)
   - Software: JetPack SDK, TensorRT, cuDNN, PyTorch

2. Raspberry Pi
   - Pi 4: 1.5GHz quad-core, 8GB RAM, $75 (CPU inference only)
   - Pi 5: 2.4GHz quad-core, 8GB RAM, $80 (2-3x faster)
   - Accelerators: Coral USB (4 TOPS), Intel Neural Compute Stick
   - Software: TFLite, ONNX Runtime, OpenVINO

3. Intel CPUs with OpenVINO
   - Optimize models for Intel CPUs/GPUs/VPUs
   - 2-5x speedup vs vanilla PyTorch/TensorFlow
   - Use: Industrial PCs, laptops, edge servers

Model Optimization:

1. Quantization
   - FP32 → INT8 (4x smaller, 2-4x faster)
   - Post-training: Calibrate with representative data
   - Quantization-aware training: Better accuracy
   - Tools: TensorRT, TFLite, ONNX Runtime

2. Pruning
   - Remove unimportant weights (sparse model)
   - Structured pruning: Remove entire filters/channels
   - 50-90% sparsity with <1% accuracy loss
   - Tools: Torchvision, NVIDIA AMP

3. Knowledge Distillation
   - Train small student model to mimic large teacher
   - Student: 10-100x smaller, 90-95% of teacher accuracy
   - Use: Deploy large model capability on edge

Deployment Workflow:
```python
# 1. Train model (PyTorch)
model = train_model(training_data)

# 2. Export to ONNX
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy_input, 'model.onnx', opset_version=13)

# 3. Optimize for edge (TensorRT for Jetson)
import tensorrt as trt
logger = trt.Logger(trt.Logger.INFO)
builder = trt.Builder(logger)
network = builder.create_network(1 << int(trt.NetworkDefinitionFlags.EXPLICIT_BATCH))
parser = trt.OnnxParser(network, logger)
parser.parse_from_file('model.onnx')
engine = builder.build_serialized_network(network)

# 4. Run inference
import pycuda.driver as cuda
context = engine.create_execution_context()
input_buf = cuda.mem_alloc(4 * 3 * 224 * 224)
output_buf = cuda.mem_alloc(4 * 1000)
context.execute(2, [int(input_buf), int(output_buf)])
```

Performance Tips:
- Use batch inference (process multiple images at once)
- Pre-allocate buffers (avoid memory allocation during inference)
- Use FP16 (half precision) on GPUs with Tensor Cores
- Profile with NVIDIA Nsight, Intel VTune""",
        domain="ai_ml",
        category="edge_ai",
        tags=["ai", "edge ai", "jetson", "tensorrt", "deployment", "optimization"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["ai-deep-learning-001"],
        examples=[
            "Jetson Orin: 40 TOPS, run YOLOv8 at 30 FPS for real-time object detection",
            "Quantization: FP32 → INT8, 4x smaller, 2-4x faster, <1% accuracy loss",
            "Deploy: torch.onnx.export() → TensorRT optimization → C++ inference",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created AI/ML domain with {len(domain.entries)} entries")
    return domain
