"""
BentoML Service Example
Adapt this template for your specific ML model
"""
import bentoml
from bentoml.io import JSON, NumpyNdarray
import numpy as np

# Load your model (example with scikit-learn)
# model_ref = bentoml.sklearn.get("my_model:latest")
# model_runner = model_ref.to_runner()

# Create BentoML service
svc = bentoml.Service("ml_service")

# Add model runner to service
# svc = bentoml.Service("ml_service", runners=[model_runner])

@svc.api(input=JSON(), output=JSON())
async def predict(input_data: dict) -> dict:
    """
    Prediction endpoint
    
    Example request:
    {
        "features": [1.0, 2.0, 3.0, 4.0]
    }
    """
    # Extract features from input
    features = np.array(input_data["features"]).reshape(1, -1)
    
    # Make prediction
    # prediction = await model_runner.predict.async_run(features)
    
    # For demo purposes, return dummy prediction
    prediction = {"prediction": 0.5, "confidence": 0.95}
    
    return prediction

@svc.api(input=NumpyNdarray(), output=NumpyNdarray())
async def predict_ndarray(input_array: np.ndarray) -> np.ndarray:
    """
    Prediction endpoint with numpy array input/output
    Useful for batch predictions
    """
    # prediction = await model_runner.predict.async_run(input_array)
    
    # For demo purposes, return dummy prediction
    return np.array([0.5] * len(input_array))

# Health check endpoint (automatically provided by BentoML at /healthz)
