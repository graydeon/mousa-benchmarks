"""Instrument a disposable source copy; never use it for wall-time adoption."""
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
functions = {
    'internal/sqlite/open.go': ['open', 'preflightWritable'],
    'internal/sqlite/migrate.go': ['verifyVersion'],
    'internal/sqlite/trail.go': ['verifySourceTrailRecords', 'getSourceTrail', 'insertSourceTrail', 'traceLexical'],
    'internal/sqlite/trail_content.go': ['verifyExactTrailContent'],
    'internal/sqlite/retrieval.go': ['lexicalEvidencePaths', 'searchEnforcedLexical'],
    'internal/sqlite/records.go': ['getSegment'],
    'internal/sqlite/policy_decision.go': ['evaluateSourceRetrieval', 'verifyPolicyDecisionRecords'],
    'internal/mousa/trail.go': ['NewSourceTrail'],
    'cmd/mousa/query.go': ['queryItems'],
    'cmd/mousa/main.go': ['emit'],
}
if len(sys.argv) > 2 and sys.argv[2] == 'allocations':
    functions = {'cmd/mousa/main.go': []}
for filename, names in functions.items():
    path = root / filename
    text = path.read_text()
    text = text.replace('import (', 'import (\n"github.com/graydeon/mousa/internal/packingdiag"', 1)
    for name in names:
        pattern = r'(?m)^(func (?:\([^\n]+\) )?' + name + r'\([^\n]+\{)\n'
        text, count = re.subn(pattern, lambda match: match[1] + '\n defer packingdiag.Stage(' + json.dumps(name) + ')()\n', text)
        if count != 1:
            raise ValueError((filename, name, count))
    if filename == 'cmd/mousa/main.go':
        text = text.replace('func main() {', 'func main() {\n defer packingdiag.Start()()')
    path.write_text(text)
path = root / 'internal/packingdiag/diag.go'
path.parent.mkdir()
path.write_text('''package packingdiag

import (
 "encoding/json"
 "os"
 "runtime"
 "runtime/pprof"
 "strings"
 "time"
)

type metric struct { Calls int; InclusiveNS int64; ExclusiveNS int64 }
type frame struct { name string; started time.Time; children int64 }
var stack []*frame
var metrics = map[string]*metric{}

// Stage is only used by the single command goroutine in diagnostic binaries.
func Stage(name string) func() {
 f := &frame{name:name, started:time.Now()}
 stack = append(stack,f)
 names := make([]string,len(stack))
 for i, value := range stack { names[i] = value.name }
 key := strings.Join(names,"/")
 return func() {
  elapsed := time.Since(f.started).Nanoseconds()
  stack = stack[:len(stack)-1]
  if len(stack)>0 { stack[len(stack)-1].children += elapsed }
  m := metrics[key]; if m==nil { m=&metric{}; metrics[key]=m }
  m.Calls++; m.InclusiveNS+=elapsed; m.ExclusiveNS+=elapsed-f.children
 }
}
func Start() func() {
 var before runtime.MemStats
 runtime.ReadMemStats(&before)
 var profile *os.File
 if name:=os.Getenv("PACKING_CPU_PROFILE"); name!="" {
  var err error
  profile,err=os.Create(name); if err!=nil { panic(err) }
  if err=pprof.StartCPUProfile(profile); err!=nil { panic(err) }
 }
 started:=time.Now()
 return func() {
  elapsed:=time.Since(started).Nanoseconds()
  if profile!=nil { pprof.StopCPUProfile(); if err:=profile.Close(); err!=nil { panic(err) } }
  var after runtime.MemStats
  runtime.ReadMemStats(&after)
  result:=map[string]any{"stages":metrics,"process_ns":elapsed,"allocated_bytes":after.TotalAlloc-before.TotalAlloc,"allocations":after.Mallocs-before.Mallocs,"gc_cycles":after.NumGC-before.NumGC}
  if err:=json.NewEncoder(os.Stderr).Encode(result); err!=nil { panic(err) }
 }
}
''')
