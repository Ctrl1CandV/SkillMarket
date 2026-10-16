我在读 Agent 方向的论文，下面是我整理的一批论文和阅读记录（JSON）。帮我做一个论文筛选页面：能快速浏览、按方向筛选、看出哪些读过，方便我挑下一篇要读的。

要求：输出一个完整的单文件 HTML（CSS 和 JS 写在文件内，不引用任何外部字体、脚本、图片或网络资源），数据直接写进页面。页面要在电脑和手机上都能用。

数据说明：标题、作者、年份、摘要首句、链接来自 arXiv；venue 为 null 表示正式发表处未确认；topics、my_status、my_note、added_on 是我自己的阅读记录。

```json
[
 {
  "arxiv_id": "2201.11903",
  "url": "https://arxiv.org/abs/2201.11903",
  "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
  "authors": [
   "Jason Wei",
   "Xuezhi Wang",
   "Dale Schuurmans",
   "Maarten Bosma",
   "Brian Ichter",
   "Fei Xia",
   "Ed Chi",
   "Quoc Le",
   "Denny Zhou"
  ],
  "year": 2022,
  "venue": "NeurIPS 2022",
  "topics": [
   "推理"
  ],
  "abstract_first_sentence": "We explore how generating a chain of thought -- a series of intermediate reasoning steps -- significantly improves the ability of large language models to perform complex reasoning.",
  "my_status": "已读",
  "my_note": "提示里给几步推理示例就能明显提升算术题，基线必读。",
  "added_on": "2026-09-08"
 },
 {
  "arxiv_id": "2210.03629",
  "url": "https://arxiv.org/abs/2210.03629",
  "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
  "authors": [
   "Shunyu Yao",
   "Jeffrey Zhao",
   "Dian Yu",
   "Nan Du",
   "Izhak Shafran",
   "Karthik Narasimhan",
   "Yuan Cao"
  ],
  "year": 2022,
  "venue": "ICLR 2023",
  "topics": [
   "推理",
   "工具"
  ],
  "abstract_first_sentence": "While large language models (LLMs) have demonstrated impressive capabilities across tasks in language understanding and interactive decision making, their abilities for reasoning (e.g.",
  "my_status": "已读",
  "my_note": "推理和行动交替进行；HotpotQA 上靠维基 API 减少幻觉。",
  "added_on": "2026-09-10"
 },
 {
  "arxiv_id": "2302.04761",
  "url": "https://arxiv.org/abs/2302.04761",
  "title": "Toolformer: Language Models Can Teach Themselves to Use Tools",
  "authors": [
   "Timo Schick",
   "Jane Dwivedi-Yu",
   "Roberto Dessì",
   "Roberta Raileanu",
   "Maria Lomeli",
   "Luke Zettlemoyer",
   "Nicola Cancedda",
   "Thomas Scialom"
  ],
  "year": 2023,
  "venue": "NeurIPS 2023",
  "topics": [
   "工具"
  ],
  "abstract_first_sentence": "Language models (LMs) exhibit remarkable abilities to solve new tasks from just a few examples or textual instructions, especially at scale.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-09-15"
 },
 {
  "arxiv_id": "2303.11366",
  "url": "https://arxiv.org/abs/2303.11366",
  "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
  "authors": [
   "Noah Shinn",
   "Federico Cassano",
   "Edward Berman",
   "Ashwin Gopinath",
   "Karthik Narasimhan",
   "Shunyu Yao"
  ],
  "year": 2023,
  "venue": "NeurIPS 2023",
  "topics": [
   "推理",
   "记忆"
  ],
  "abstract_first_sentence": "Large language models (LLMs) have been increasingly used to interact with external environments (e.g., games, compilers, APIs) as goal-driven agents.",
  "my_status": "在读",
  "my_note": "读到第 4 节，反思文本存进记忆再重试，想对比 Self-Refine。",
  "added_on": "2026-09-18"
 },
 {
  "arxiv_id": "2303.17651",
  "url": "https://arxiv.org/abs/2303.17651",
  "title": "Self-Refine: Iterative Refinement with Self-Feedback",
  "authors": [
   "Aman Madaan",
   "Niket Tandon",
   "Prakhar Gupta",
   "Skyler Hallinan",
   "Luyu Gao",
   "Sarah Wiegreffe",
   "Uri Alon",
   "Nouha Dziri",
   "Shrimai Prabhumoye",
   "Yiming Yang",
   "Shashank Gupta",
   "Bodhisattwa Prasad Majumder",
   "Katherine Hermann",
   "Sean Welleck",
   "Amir Yazdanbakhsh",
   "Peter Clark"
  ],
  "year": 2023,
  "venue": "NeurIPS 2023",
  "topics": [
   "推理"
  ],
  "abstract_first_sentence": "Like humans, large language models (LLMs) do not always generate the best output on their first try.",
  "my_status": "已读",
  "my_note": "同一模型生成、反馈、改写三步循环，不需要额外训练。",
  "added_on": "2026-09-20"
 },
 {
  "arxiv_id": "2304.03442",
  "url": "https://arxiv.org/abs/2304.03442",
  "title": "Generative Agents: Interactive Simulacra of Human Behavior",
  "authors": [
   "Joon Sung Park",
   "Joseph C. O'Brien",
   "Carrie J. Cai",
   "Meredith Ringel Morris",
   "Percy Liang",
   "Michael S. Bernstein"
  ],
  "year": 2023,
  "venue": "UIST 2023",
  "topics": [
   "记忆"
  ],
  "abstract_first_sentence": "Believable proxies of human behavior can empower interactive applications ranging from immersive environments to rehearsal spaces for interpersonal communication to prototyping tools.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-09-22"
 },
 {
  "arxiv_id": "2305.10601",
  "url": "https://arxiv.org/abs/2305.10601",
  "title": "Tree of Thoughts: Deliberate Problem Solving with Large Language Models",
  "authors": [
   "Shunyu Yao",
   "Dian Yu",
   "Jeffrey Zhao",
   "Izhak Shafran",
   "Thomas L. Griffiths",
   "Yuan Cao",
   "Karthik Narasimhan"
  ],
  "year": 2023,
  "venue": "NeurIPS 2023",
  "topics": [
   "推理"
  ],
  "abstract_first_sentence": "Language models are increasingly being deployed for general problem solving across a wide range of tasks, but are still confined to token-level, left-to-right decision-making processes during inference.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-09-25"
 },
 {
  "arxiv_id": "2305.16291",
  "url": "https://arxiv.org/abs/2305.16291",
  "title": "Voyager: An Open-Ended Embodied Agent with Large Language Models",
  "authors": [
   "Guanzhi Wang",
   "Yuqi Xie",
   "Yunfan Jiang",
   "Ajay Mandlekar",
   "Chaowei Xiao",
   "Yuke Zhu",
   "Linxi Fan",
   "Anima Anandkumar"
  ],
  "year": 2023,
  "venue": null,
  "topics": [
   "具身",
   "工具"
  ],
  "abstract_first_sentence": "We introduce Voyager, the first LLM-powered embodied lifelong learning agent in Minecraft that continuously explores the world, acquires diverse skills, and makes novel discoveries without human intervention.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-09-27"
 },
 {
  "arxiv_id": "2308.03688",
  "url": "https://arxiv.org/abs/2308.03688",
  "title": "AgentBench: Evaluating LLMs as Agents",
  "authors": [
   "Xiao Liu",
   "Hao Yu",
   "Hanchen Zhang",
   "Yifan Xu",
   "Xuanyu Lei",
   "Hanyu Lai",
   "Yu Gu",
   "Hangliang Ding",
   "Kaiwen Men",
   "Kejuan Yang",
   "Shudan Zhang",
   "Xiang Deng",
   "Aohan Zeng",
   "Zhengxiao Du",
   "Chenhui Zhang",
   "Sheng Shen",
   "Tianjun Zhang",
   "Yu Su",
   "Huan Sun",
   "Minlie Huang",
   "Yuxiao Dong",
   "Jie Tang"
  ],
  "year": 2023,
  "venue": "ICLR 2024",
  "topics": [
   "评测"
  ],
  "abstract_first_sentence": "The potential of Large Language Model (LLM) as agents has been widely acknowledged recently.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-10-02"
 },
 {
  "arxiv_id": "2308.11432",
  "url": "https://arxiv.org/abs/2308.11432",
  "title": "A Survey on Large Language Model based Autonomous Agents",
  "authors": [
   "Lei Wang",
   "Chen Ma",
   "Xueyang Feng",
   "Zeyu Zhang",
   "Hao Yang",
   "Jingsen Zhang",
   "Zhiyuan Chen",
   "Jiakai Tang",
   "Xu Chen",
   "Yankai Lin",
   "Wayne Xin Zhao",
   "Zhewei Wei",
   "Ji-Rong Wen"
  ],
  "year": 2023,
  "venue": "Frontiers of Computer Science 2024",
  "topics": [
   "综述"
  ],
  "abstract_first_sentence": "Autonomous agents have long been a prominent research focus in both academic and industry communities.",
  "my_status": "在读",
  "my_note": "按“构建—应用—评测”三部分组织，先读构建部分。",
  "added_on": "2026-10-05"
 },
 {
  "arxiv_id": "2310.06770",
  "url": "https://arxiv.org/abs/2310.06770",
  "title": "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?",
  "authors": [
   "Carlos E. Jimenez",
   "John Yang",
   "Alexander Wettig",
   "Shunyu Yao",
   "Kexin Pei",
   "Ofir Press",
   "Karthik Narasimhan"
  ],
  "year": 2023,
  "venue": "ICLR 2024",
  "topics": [
   "评测"
  ],
  "abstract_first_sentence": "Language models have outpaced our ability to evaluate them effectively, but for their future development it is essential to study the frontier of their capabilities.",
  "my_status": "未读",
  "my_note": null,
  "added_on": "2026-10-08"
 },
 {
  "arxiv_id": "2310.08560",
  "url": "https://arxiv.org/abs/2310.08560",
  "title": "MemGPT: Towards LLMs as Operating Systems",
  "authors": [
   "Charles Packer",
   "Sarah Wooders",
   "Kevin Lin",
   "Vivian Fang",
   "Shishir G. Patil",
   "Ion Stoica",
   "Joseph E. Gonzalez"
  ],
  "year": 2023,
  "venue": null,
  "topics": [
   "记忆"
  ],
  "abstract_first_sentence": "Large language models (LLMs) have revolutionized AI, but are constrained by limited context windows, hindering their utility in tasks like extended conversations and document analysis.",
  "my_status": "在读",
  "my_note": "把上下文当内存分层管理，读到 2.3。",
  "added_on": "2026-10-11"
 }
]
```
