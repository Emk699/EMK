import sys, shutil, os
from gradio_client import Client, handle_file
n = sys.argv[1]; S = os.environ.get("TRAB", os.path.dirname(os.path.abspath(__file__)))
c = Client("trellis-community/TRELLIS", token=os.environ.get("HF_TOKEN"))
try: c.predict(api_name="/start_session")
except Exception as e: print("start_session:", e)
r = c.predict(image=handle_file(f"{S}/cut/{n}.png"), multiimages=[], seed=0, ss_guidance_strength=7.5,
              ss_sampling_steps=12, slat_guidance_strength=3.0, slat_sampling_steps=12,
              multiimage_algo="stochastic", mesh_simplify=0.95, texture_size=1024,
              api_name="/generate_and_extract_glb")
print(r)
glb = r[1] if isinstance(r[1], str) else r[2]
shutil.copy(glb, f"{S}/tr/{n}.glb"); print("ok", n)
