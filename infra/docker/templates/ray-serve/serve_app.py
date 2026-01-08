"""
Ray Serve Application Example
Multi-model serving with auto-scaling
"""
from ray import serve
from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np

# Create FastAPI app
app = FastAPI()

# Define request/response models
class PredictionRequest(BaseModel):
    features: list[float]

class PredictionResponse(BaseModel):
    prediction: float
    model_version: str

# Define Ray Serve deployment with autoscaling
@serve.deployment(
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 10,
        "target_num_ongoing_requests_per_replica": 5,
    },
    ray_actor_options={"num_cpus": 1}
)
@serve.ingress(app)
class MLModel:
    def __init__(self):
        # Load your model here
        # self.model = load_model()
        self.model_version = "v1.0.0"
    
    @app.get("/-/health")
    async def health(self):
        """Ray Serve native health check endpoint"""
        return {"status": "healthy"}
    
    @app.post("/predict", response_model=PredictionResponse)
    async def predict(self, request: PredictionRequest):
        # Convert features to numpy array
        features = np.array(request.features).reshape(1, -1)
        
        # Make prediction
        # prediction = self.model.predict(features)[0]
        
        # For demo purposes, return dummy prediction
        prediction = 0.5
        
        return PredictionResponse(
            prediction=prediction,
            model_version=self.model_version
        )

# Deploy the application
deployment = MLModel.bind()
serve.run(deployment, host="0.0.0.0", port=8000)
