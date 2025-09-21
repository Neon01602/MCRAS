import streamlit as st
import pandas as pd
import numpy as np
import torch
from mcras.model import MCRAS
from mcras.data_loader import preprocess_input

st.set_page_config(page_title="MCRAS Streamlit App", layout="wide")

st.title("🏆 MCRAS – Multi-Channel Recurrent Attention System")
st.markdown("""
This app allows you to test the **MCRAS model** for multi-channel time-series data.
Upload your dataset, configure the model, and get predictions instantly.
""")

# Sidebar for configuration
st.sidebar.header("Model Configuration")
input_size = st.sidebar.number_input("Input Size", min_value=1, value=128)
hidden_size = st.sidebar.number_input("Hidden Size", min_value=1, value=64)
num_channels = st.sidebar.number_input("Number of Channels", min_value=1, value=8)
num_classes = st.sidebar.number_input("Number of Classes", min_value=1, value=10)

# File uploader
uploaded_file = st.file_uploader("Upload CSV file for inference", type=["csv"])

if uploaded_file is not None:
    st.write("### Uploaded Data Preview")
    df = pd.read_csv(uploaded_file)
    st.dataframe(df.head())

    # Preprocess input
    st.write("### Preprocessing Data")
    try:
        X = preprocess_input(df, num_channels=num_channels, input_size=input_size)
        st.success("Data preprocessing complete!")
        st.write("Input Shape:", X.shape)
    except Exception as e:
        st.error(f"Error in preprocessing: {e}")

    # Initialize model
    st.write("### Initializing MCRAS Model")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MCRAS(input_size=input_size, hidden_size=hidden_size, num_channels=num_channels, num_classes=num_classes)
    model.to(device)
    model.eval()
    st.success("Model initialized!")

    # Run inference
    st.write("### Running Inference")
    try:
        X_tensor = torch.tensor(X, dtype=torch.float32).to(device)
        with torch.no_grad():
            outputs = model(X_tensor)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
        st.success("Inference complete!")
        st.write("### Predictions")
        st.write(preds)
    except Exception as e:
        st.error(f"Error during inference: {e}")

st.write("---")
st.markdown("Developed using **Streamlit** and the **MCRAS model**.")
