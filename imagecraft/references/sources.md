# 版本与来源

资料核验：2026-11-01。下列链接用于核对来源，不要求每次生成联网查询。安装时以随技能发布的固定清单为准；来源的 main 分支或网页可能变化，不能据此自动更新现有安装。

## 模型组件

- [BFL FLUX.2 klein 4B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8)，revision `5b4408e59397a4a37ccb46afe426d8ed86379441`，Apache-2.0；使用 distilled FP8，不是训练用 base 或 9B 版本。
- [Comfy-Org FLUX.2 Klein 4B 组件](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B)，revision `5b3abca5c0dc1ecd4eaf3340868d09063fc1c965`，模型卡标注 Apache-2.0；使用 `qwen_3_4b.safetensors` 与 `flux2-vae.safetensors`。
- 大小、完整 SHA-256、仓库内相对路径及本地布局都在 [`models/flux-klein-4b.json`](../models/flux-klein-4b.json)。同名 VAE 在其他仓库可能是不同序列化版本；这里固定 Klein 包中的文件，不混用 Flux.2 dev 仓库的不同哈希。

这里只分发下载清单和调用代码，不分发模型权重。Apache-2.0 的模型许可不免除肖像权、商标、隐私或素材授权要求；商业使用前仍须核对相关来源及实际输入/输出的权利。不能把其他 FLUX 版本的许可或性能沿用到本配置。

## ComfyUI 与工作流

- [FLUX.2 klein 官方教程](https://docs.comfy.org/tutorials/flux/flux-2-klein)
- [文生图官方模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2_klein_text_to_image.json)
- [4B distilled 编辑官方模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2_klein_image_edit_4b_distilled.json)
- [ComfyUI API 示例](https://docs.comfy.org/development/comfyui-server/api-examples)
- [ComfyUI 原生 FLUX 节点](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_flux.py)

本技能把所需原生节点连成小型 API graph，不直接执行从网页下载的任意工作流，不加载模板里的第三方节点或 Python。主要路径是 `UNETLoader + CLIPLoader(flux2) + VAELoader → CLIPTextEncode → CFGGuider(1) + Flux2Scheduler(4) + Euler → SamplerCustomAdvanced → VAEDecode → SaveImage`；编辑在正负条件中接入 `ReferenceLatent`。

`/object_info` 预检不能替代服务器验证和真实生成。安全启动器还需所选 ComfyUI 支持其安全参数；不支持时停止并说明，不悄悄删掉禁用云节点或本地监听限制。
