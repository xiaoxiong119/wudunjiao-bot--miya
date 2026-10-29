import unittest, tempfile, pathlib, sqlite3, json, zipfile
from unittest.mock import patch
import bridge as b

class Commands(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
  self.original=b.db; b.db=sqlite3.connect(':memory:')
  b.db.executescript('create table done(id text primary key);create table attachments(scope text,path text,received real,mid text unique);create table pending(scope text primary key,command text,mid text,started real,expires real);')
  self.replies=[];self.runs=[]
  self.p1=patch.object(b,'reply',side_effect=lambda *a:self.replies.append(a));self.p1.start()
  self.p2=patch.object(b,'run_skill',side_effect=lambda *a:self.runs.append(a));self.p2.start()
  self.file=self.root/'script.pdf';self.file.write_bytes(b'%PDF-1.7')
 def tearDown(self):
  self.p1.stop();self.p2.stop();b.db.close();b.db=self.original;self.tmp.cleanup()
 def event(self,t=1000,user='u1',chat='c1',text='/jbfj'):
  return dict(chat_id=chat,sender_id=user,create_time=str(t*1000),content=text)
 def test_progress_uses_real_stage_and_file_count(self):
  import time
  progress=self.root/'progress.json';progress.write_text('{"stage":"已读取正文；正在提取场景"}')
  (self.root/'assets.xlsx').write_bytes(b'xlsx')
  report=b.progress_report(progress,self.root,time.monotonic()-301,{str(self.file):(self.file.stat().st_mtime_ns,self.file.stat().st_size)})
  self.assertIn('已读取正文',report);self.assertIn('1 个文件',report);self.assertIn('5 分钟',report)
 def test_progress_no_fabricated_stage(self):
  import time
  report=b.progress_report(self.root/'missing',self.root,time.monotonic(),{})
  self.assertIn('暂无新的已确认',report)
 def test_running_process_reports_and_finishes(self):
  import sys,os
  p=b.execute_with_progress([sys.executable,'-c','import sys,time; x=sys.stdin.read();time.sleep(0.18);print(x)'],'hello',os.environ.copy(),'mid',self.root/'missing',self.root,{},interval=0.05)
  self.assertEqual(p.returncode,0);self.assertEqual(p.stdout.strip(),'hello')
  self.assertGreaterEqual(len(self.replies),1)
 def test_fast_process_has_no_progress_spam(self):
  import sys,os
  p=b.execute_with_progress([sys.executable,'-c','print("done")'],'',os.environ.copy(),'mid',self.root/'missing',self.root,{},interval=1)
  self.assertEqual(p.returncode,0);self.assertFalse(self.replies)
 def test_skill_starts_once_and_does_not_request_confirmation(self):
  self.p2.stop()
  try:
   with patch.object(b,'check_environment'),patch.object(b,'run_agent') as agent:
    b.run_skill('/mscf',str(self.file),'mid',self.event())
    self.assertEqual(len(self.replies),1)
    self.assertIn('已开始执行',self.replies[0][1])
    self.assertIn('禁止先调用 screenplay-episode-processor',agent.call_args.args[2])
    self.assertEqual(agent.call_args.kwargs['contract']['kind'],'art')
  finally:self.p2.start()
 def write_workbook(self,path):
  names=['全剧汇总','分集明细','场景统计','人物统计','道具统计','人物物品变化']
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets>'+''.join('<sheet name="'+n+'"/>' for n in names)+'</sheets></workbook>')
   z.writestr('xl/worksheets/sheet1.xml','<worksheet><c r="A1"/></worksheet>')
 def test_artifact_validator_rejects_old_corrupt_and_empty_files(self):
  bad=self.root/'bad.xlsx';bad.write_bytes(b'not excel')
  self.assertFalse(b.generated_workbooks(self.root,{}))
  good=self.root/'good.xlsx';self.write_workbook(good)
  self.assertEqual(b.generated_workbooks(self.root,{}),[good])
  before={str(good):(good.stat().st_mtime_ns,good.stat().st_size)}
  self.assertFalse(b.generated_workbooks(self.root,before))
 def test_premature_exit_resumes_before_returning(self):
  import subprocess
  out=self.root/'answer.txt';calls=[]
  def execute(argv,*args,**kwargs):
   calls.append(argv);out.write_text('未完成' if len(calls)==1 else '已完成')
   if len(calls)==2:self.write_workbook(self.root/'result.xlsx')
   return subprocess.CompletedProcess(argv,0,'{"type":"thread.started","thread_id":"test-session"}\n','')
  with patch.object(b,'execute_with_progress',side_effect=execute):
   result=b.run_until_artifact('work',{},'m',self.root/'progress.json',self.root,{},out,True)
  self.assertEqual(result,'已完成');self.assertEqual(len(calls),2)
  self.assertIn('resume',calls[1]);self.assertIn('test-session',calls[1])
  self.assertLess(calls[1].index('-s'),calls[1].index('resume'))
  self.assertEqual(calls[1][calls[1].index('-s')+1],'workspace-write')
  self.assertEqual(calls[0][calls[0].index('-C')+1],str(self.root))
 def test_no_artifact_never_counts_as_success(self):
  import subprocess
  out=self.root/'answer.txt'
  with patch.object(b,'execute_with_progress',return_value=subprocess.CompletedProcess([],0,'','')):
   with self.assertRaisesRegex(RuntimeError,'仍未生成'):
    b.run_until_artifact('work',{},'m',self.root/'progress.json',self.root,{},out,True)
 def test_delivery_sends_attachment_then_confirmation_and_receipt(self):
  (self.root/'state').mkdir();f=self.root/'result.xlsx';self.write_workbook(f)
  with patch.object(b,'ROOT',self.root),patch.object(b,'cli',return_value={'ok':True,'data':{'message_id':'om_delivered'}}) as send:
   receipts=b.deliver_results('om_source','unused local file link',self.root,{str(self.file):(self.file.stat().st_mtime_ns,self.file.stat().st_size)})
  self.assertEqual(len(receipts),1);self.assertIn('--file',send.call_args.args)
  self.assertIn('om_source',send.call_args.args)
  self.assertIn('已发送 1 个结果附件',self.replies[0][1])
  self.assertEqual(len(list((self.root/'state').glob('delivery-*.json'))),1)
 def test_delivery_failure_does_not_claim_completion(self):
  f=self.root/'result.xlsx';self.write_workbook(f)
  with patch.object(b,'ROOT',self.root),patch.object(b,'cli',side_effect=RuntimeError('upload failed')):
   with self.assertRaises(RuntimeError):b.deliver_results('om_source','unused',self.root,{})
  self.assertFalse(self.replies)
 def test_environment_checks_configured_python(self):
  from types import SimpleNamespace
  with patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
   b.check_environment()
   self.assertEqual(run.call_args.args[0][0],b.PYTHON)
   self.assertIn('import docx',run.call_args.args[0][2])
 def test_help_does_not_call_agent(self):
  self.assertTrue(b.route_command(self.event(text='/help'),'h'));self.assertIn('/mscf',self.replies[0][1]);self.assertFalse(self.runs)
 def test_recent_script(self):
  b.register_attachment(self.event(999),'f',self.file)
  b.route_command(self.event(),'m');self.assertEqual(self.runs[0][1],str(self.file))
 def test_wait_at_boundary_and_once(self):
  b.route_command(self.event(),'m')
  self.assertTrue(b.register_attachment(self.event(1300),'f',self.file))
  self.assertFalse(b.register_attachment(self.event(1301),'f2',self.file));self.assertEqual(len(self.runs),1)
 def test_expired(self):
  b.route_command(self.event(),'m');b.register_attachment(self.event(1301),'f',self.file)
  self.assertFalse(self.runs);self.assertIn('超过五分钟',self.replies[-1][1])
 def test_user_and_chat_isolation(self):
  b.route_command(self.event(),'m')
  b.register_attachment(self.event(1001,user='u2'),'f',self.file)
  b.register_attachment(self.event(1001,chat='c2'),'f2',self.file)
  self.assertFalse(self.runs)
  self.assertTrue(b.register_attachment(self.event(1002),'f3',self.file))
 def test_command_replaces_pending(self):
  b.route_command(self.event(),'m');b.route_command(self.event(1001,text='/mscf'),'n')
  b.register_attachment(self.event(1002),'f',self.file);self.assertEqual(self.runs[0][0],'/mscf')
 def test_mentions_and_unknown(self):
  e=self.event(text='@_user_1 /help');e['mentions']=[{'key':'@_user_1'}]
  self.assertTrue(b.route_command(e,'m'));self.assertIn('当前能力',self.replies[-1][1])
  b.route_command(self.event(text='/unknown'),'n');self.assertIn('未知命令',self.replies[-1][1])
 def test_file_formats(self):
  self.assertEqual(b.script_extension(self.file),'.pdf')
  doc=self.root/'doc';
  with zipfile.ZipFile(doc,'w') as z:z.writestr('word/document.xml','<document/>')
  self.assertEqual(b.script_extension(doc),'.docx')
  doc.write_bytes(b'not a script');self.assertIsNone(b.script_extension(doc))
 def test_latest_file_selected(self):
  b.register_attachment(self.event(900),'f1',self.file)
  other=self.root/'new.pdf';other.write_bytes(b'%PDF-')
  b.register_attachment(self.event(999),'f2',other)
  b.route_command(self.event(),'m');self.assertEqual(self.runs[0][1],str(other))

if __name__=='__main__':unittest.main()
