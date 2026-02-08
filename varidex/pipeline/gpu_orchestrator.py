# File: varidex/pipeline/gpu_orchestrator.py (NEW ~150 lines)

class SmartPipeline:
    def __init__(self):
        self.gpu_available = self._detect_gpu()
        self.mode = "GPU" if self.gpu_available else "CPU"
        
    def _detect_gpu(self) -> bool:
        """Detect ROCm GPU (AMD) or CUDA (NVIDIA)"""
        try:
            import torch
            import cudf
            
            # Check AMD ROCm (your RX 7900 XT)
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                print(f"✅ GPU DETECTED: {gpu_name}")
                print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
                return True
            
            # Fallback check
            print("⚠️  No GPU detected - using optimized CPU")
            return False
            
        except ImportError:
            print("ℹ️  GPU libraries not installed - using CPU")
            return False

    def run(self, args):
        print(f"🚀 Starting {self.mode} pipeline...")
        
        if self.mode == "GPU":
            return self._run_gpu_pipeline(args)
        else:
            return self._run_cpu_pipeline(args)  # Existing code!
