"""Local end-to-end replay of the received screenplay; does not send Feishu messages."""
import bridge as b, sqlite3, pathlib,os,json
runtime=pathlib.Path.home()/'Library/Application Support/WulvchaBridge'
row=sqlite3.connect(runtime/'state/bridge.sqlite').execute('select path from attachments order by received desc limit 1').fetchone()
b.ROOT=runtime
source=pathlib.Path(row[0]);folder=runtime/'downloads'/'verified-recovery';folder.mkdir(exist_ok=True)
progress=runtime/'state/recovery.progress.json';out=runtime/'state/recovery.answer.txt'
b.reply=lambda mid,text:print(text,flush=True)
prompt='请直接完成美术资产拆分，不要只解释或汇报未完成。用户授权一次性完成，不需要确认。必须先读取 /Users/fanxiaoli/.codex/skills/screenplay-element-breakdown/SKILL.md 和 references/extraction-rules.md。输入是第34至40集分集剧本，源文件：'+str(source)+'。读取全部正文，按集按场提取全部场景、人物、明确服装、道具及物品变化，保留原始集号，生成完整六 Sheet Excel，包含角色音色、道具提示词、场景正反打各两版提示词。使用技能 scripts/build_excel.py。输出 data.json 与 Excel 必须保存到 '+str(folder)+'。Python必须使用 '+b.PYTHON+'。进度写入 '+str(progress)+'，格式 {"stage":"真实阶段进展"}。必须实际生成 Excel 并验证其覆盖全部剧本场次后再结束。不要发送飞书消息。'
env=os.environ.copy();env['PATH']=str(pathlib.Path(b.PYTHON).parent)+os.pathsep+env.get('PATH','')
print(b.run_until_artifact(prompt,env,'local-test',progress,folder,{},out,True),flush=True)
