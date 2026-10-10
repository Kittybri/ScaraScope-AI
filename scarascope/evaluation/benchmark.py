"""Run reproducible, key-free arithmetic benchmark with explicit case coverage."""
from math import isclose
from pydantic import BaseModel
from .golden import built_in_cases

class CaseResult(BaseModel):
    id: str
    label: str
    passed: bool
    expected: float | None
    actual: float | None

class BenchmarkResult(BaseModel):
    suite: str = "ScaraScope deterministic golden tests"
    passed: int
    total: int
    accuracy_pct: float
    results: list[CaseResult]
    limitation: str = "This benchmark tests deterministic arithmetic only. It is not an LLM accuracy, SEC document RAG, or FinanceBench score."


def run_benchmark() -> BenchmarkResult:
    output=[]
    for case in built_in_cases():
        equal = (case.expected is None and case.observed is None) or (
            case.expected is not None and case.observed is not None and isclose(case.expected,case.observed,rel_tol=1e-8,abs_tol=1e-4))
        output.append(CaseResult(id=case.id,label=case.label,passed=equal,expected=case.expected,actual=case.observed))
    passed=sum(c.passed for c in output)
    return BenchmarkResult(passed=passed,total=len(output),accuracy_pct=round(100*passed/len(output),2),results=output)

if __name__=="__main__":
    import json
    print(json.dumps(run_benchmark().model_dump(),indent=2))
