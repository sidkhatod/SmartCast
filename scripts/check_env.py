import torch

def check_environment():
    print("=== Environment Check ===")
    print(f"PyTorch Version: {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        device_count = torch.cuda.device_count()
        print(f"CUDA Device Count: {device_count}")
        for i in range(device_count):
            print(f"  Device {i}: {torch.cuda.get_device_name(i)}")
            
        print("\n--- Testing Tensor Transfer ---")
        try:
            tensor = torch.tensor([1.0, 2.0, 3.0])
            print("CPU Tensor:", tensor)
            
            tensor = tensor.to("cuda")
            print("CUDA Tensor:", tensor)
            
            tensor = tensor.cpu()
            print("Round-trip complete.")
            print("GPU IS WORKING CORRECTLY!")
        except Exception as e:
            print("FAILED to transfer tensor to GPU!")
            print(e)
    else:
        print("\nWARNING: CUDA is NOT available. This script will run on CPU and be extremely slow.")

if __name__ == "__main__":
    check_environment()
