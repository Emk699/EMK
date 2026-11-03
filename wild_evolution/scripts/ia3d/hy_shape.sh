#!/bin/bash
# gera forma no Hunyuan3D-2 e baixa o glb
S=$(dirname $0); n=$1
out=$(API=/shape_generation STEPS=30 timeout 600 $S/venv/bin/python $S/hy_gen.py $n 2>&1)
P=$(echo "$out" | grep -o "/tmp/gradio/[^']*white_mesh.glb" | head -1)
if [ -z "$P" ]; then echo "$n FALHOU: $(echo "$out" | tail -1)"; exit 1; fi
curl -sS -o $S/hy/${n}_forma.glb "https://tencent-hunyuan3d-2.hf.space/file=$P" && echo "$n ok"
