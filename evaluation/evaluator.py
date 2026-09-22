import time
from typing import List, Dict, Any

class PipelineDiagnostics:
    def __init__(self):
        self.timings = {}
        self.start_times = {}

    def start(self, stage_name: str):
        self.start_times[stage_name] = time.perf_counter()

    def stop(self, stage_name: str):
        if stage_name in self.start_times:
            elapsed = time.perf_counter() - self.start_times[stage_name]
            self.timings[stage_name] = elapsed

    def generate_report(self, question: str, retrieved_docs: List[Dict], answer: str, final_context: str):
        total_time = sum(self.timings.values())
        bottleneck = max(self.timings.items(), key=lambda x: x[1]) if self.timings else ("None", 0.0)

        print("\n" + "=" * 80)
        print("                 PIPELINE DIAGNOSTICS & TELEMETRY")
        print("=" * 80)

        # 1. LATENCY & BOTTLENECK ANALYSIS
        print(f"\n[1] LATENCY BREAKDOWN (Total: {total_time:.3f}s)")
        print("-" * 80)
        print(f"{'Stage':<25} | {'Latency':<10} | {'Share of Runtime'}")
        print("-" * 80)
        for stage, duration in self.timings.items():
            pct = (duration / total_time * 100) if total_time > 0 else 0
            print(f"{stage:<25} | {duration*1000:>7.1f} ms | {pct:>5.1f}%")
        print("-" * 80)
        print(f"BOTTLENECK: [{bottleneck[0]}] taking {(bottleneck[1]/total_time*100):.1f}% of total time.")

        # 2. FINAL CONTEXT CHUNKS
        print(f"\n[2] FINAL CONTEXT CHUNKS (Top {len(retrieved_docs)})")
        print("-" * 80)
        print(f"{'Rank':<4} | {'Score':<7} | {'Source':<30} | {'Chunk ID'}")
        print("-" * 80)
        
        for idx, doc in enumerate(retrieved_docs, 1):
            # SAFELY check if doc is a dictionary before using .get()
            if isinstance(doc, dict):
                score = doc.get("rerank_score", doc.get("score", 0.0))
                score_str = f"{score:>7.4f}" if isinstance(score, (float, int)) else f"{score:>7}"
                source = str(doc.get("source", "unknown"))[:28]
                chunk_id = doc.get("chunk_id", "N/A")
            else:
                score_str = "  N/A  "
                source = "Raw Text String"
                chunk_id = "N/A"
                
            print(f"{idx:<4} | {score_str} | {source:<30} | {chunk_id}")

        # 3. GENERATION QUALITY METRICS
        # SAFELY check for dictionaries when extracting unique sources
        unique_sources = set(
            doc.get("source") for doc in retrieved_docs 
            if isinstance(doc, dict) and "source" in doc
        )
        
        words_in_answer = set(answer.lower().split())
        words_in_context = set(final_context.lower().split())
        grounding = (len(words_in_answer.intersection(words_in_context)) / len(words_in_answer) * 100) if words_in_answer else 0

        print(f"\n[3] GENERATION QUALITY METRICS")
        print("-" * 80)
        print(f"Final Context Size     : {len(final_context)} chars (~{len(final_context)//4} tokens)")
        print(f"Unique Sources Cited   : {len(unique_sources)} ({', '.join(unique_sources)})")
        print(f"Answer Length          : {len(answer)} chars (~{len(answer)//4} tokens)")
        print(f"Context Grounding      : {grounding:.1f}% of answer vocabulary exists in context")
        print("=" * 80 + "\n")