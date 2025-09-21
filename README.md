# 🏆 MCRAS – Multi-Channel Recurrent Attention System

MCRAS is a deep learning framework for multi-channel time-series data analysis.
It combines Recurrent Neural Networks (RNNs) with Attention mechanisms to model temporal
and inter-channel dependencies.

---

## 🚀 Features

* **Multi-Channel Input** – Process multiple channels simultaneously  
* **Recurrent Architecture** – Capture temporal dependencies  
* **Attention Mechanism** – Focus on important channels and time steps  
* **Scalable & Efficient** – Handles large datasets effectively  

---

## 📂 Project Structure

MCRAS/  
* `requirements.txt` – Python dependencies  
* `train.py` – Training script  
* `evaluate.py` – Evaluation script  
* `mcras/` – Core model package  
  * `__init__.py`  
  * `model.py` – RNN + Attention model  
  * `train_utils.py` – Training utilities  
  * `eval_utils.py` – Evaluation utilities  
  * `data_loader.py` – Data loading functions  
* `data/` – Sample datasets  
* `notebooks/` – Optional Jupyter notebooks  

---

## 🛠️ Installation & Setup

1. **Clone the repository**  
git clone https://github.com/Neon01602/MCRAS.git
cd MCRAS

markdown
Copy code

2. **Create a virtual environment**  
python -m venv env
source env/bin/activate # For Linux/Mac
env\Scripts\activate # For Windows

markdown
Copy code

3. **Install dependencies**  
pip install -r requirements.txt

yaml
Copy code

---

## ⚡ Usage

* **Data Format**  
  * Input → 3D tensor: `(num_samples, num_channels, num_timesteps)`  
  * Output → 2D tensor: `(num_samples, num_classes)`  

* **Model Initialization**  
from mcras import MCRAS

model = MCRAS(input_size=128, hidden_size=64, num_channels=8, num_classes=10)

markdown
Copy code

* **Training**  
from mcras import train

train(model, train_loader, val_loader, epochs=50, lr=0.001)

markdown
Copy code

* **Evaluation**  
from mcras import evaluate

accuracy = evaluate(model, test_loader)
print("Test Accuracy:", accuracy)

yaml
Copy code

---

## 🧩 Model Architecture

* **Input Layer** – Accepts multi-channel time-series data  
* **RNN Layers** – Capture temporal dependencies  
* **Attention Layer** – Focus on important channels & timesteps  
* **Fully Connected Layer** – Predict output classes  

---

## 📈 Training Workflow

* Load datasets (train & validation)  
* Initialize MCRAS model  
* Choose loss function → Cross-Entropy  
* Optimizer → Adam with learning rate scheduler  
* Run training loop and update weights per epoch  

---
