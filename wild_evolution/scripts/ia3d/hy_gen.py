import sys, shutil, os
from gradio_client import Client, handle_file
name = sys.argv[1]; S = os.environ.get("TRAB", os.path.dirname(os.path.abspath(__file__)))
c = Client("tencent/Hunyuan3D-2")
r = c.predict(caption=None, image=handle_file(f"{S}/cut/{name}.png"), mv_image_front=None, mv_image_back=None,
              mv_image_left=None, mv_image_right=None, steps=int(os.environ.get("STEPS",30)), guidance_scale=5.0, seed=1234,
              octree_resolution=256, check_box_rembg=True, num_chunks=8000, randomize_seed=False,
              api_name=os.environ.get("API","/generation_all"))
print(r)
for i, f in enumerate([x for x in r if isinstance(x,str) and os.path.isfile(x)]):
    ext = os.path.splitext(f)[1]
    shutil.copy(f, f"{S}/hy/{name}_{'forma' if i == 0 else 'textura'}{ext}")
