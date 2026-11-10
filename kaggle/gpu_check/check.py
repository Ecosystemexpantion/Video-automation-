import subprocess, torch
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        print(f"GPU {i}: {p.name} {p.total_memory // 2**30} GB")
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
