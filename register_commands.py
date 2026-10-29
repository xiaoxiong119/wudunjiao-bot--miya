"""Register the local command catalog in Feishu. Requires only slash-command write scope."""
import json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parent
CLI='/Users/fanxiaoli/.codebuddy/bin/lark-cli'
def main():
 catalog=json.loads((ROOT/'commands.json').read_text())
 state=ROOT/'state/slash-registration.json'
 saved=json.loads(state.read_text()) if state.exists() else {}
 for command,spec in catalog.items():
  if command in saved: continue
  proc=subprocess.run([CLI,'--profile','wulvcha','application','+slash-command-create','--as','bot','--command',command.lstrip('/'),'--description',spec['description']],text=True,capture_output=True)
  if proc.returncode:
   print(proc.stdout or proc.stderr)
   return proc.returncode
  result=json.loads(proc.stdout)
  if result.get('ok') is False:
   print(proc.stdout);return 1
  saved[command]=result
  state.parent.mkdir(exist_ok=True)
  state.write_text(json.dumps(saved,ensure_ascii=False,indent=2))
  print('已注册 '+command)
 return 0
if __name__=='__main__':raise SystemExit(main())
