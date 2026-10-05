import kagglehub

# Download latest version
path = kagglehub.model_download("google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct")

print("Path to model files:", path)