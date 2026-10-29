"""Deterministic file naming, validation, and Word-only episode packaging."""
import pathlib,zipfile,xml.etree.ElementTree as ET,subprocess,json,re

def valid_docx(path):
 try:
  if path.is_symlink():return False
  with zipfile.ZipFile(path) as z:
   ET.fromstring(z.read('word/document.xml'))
   return z.testzip() is None
 except (OSError,KeyError,ValueError,zipfile.BadZipFile,ET.ParseError):return False

def heading_count(path):
 with zipfile.ZipFile(path) as z:
  root=ET.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 return sum(1 for style in root.findall('.//w:pPr/w:pStyle',ns) if style.get('{'+ns['w']+'}val')=='Heading1')

def pdf_has_toc(path,python):
 if not path.is_file() or path.is_symlink():return False
 code='import pymupdf,sys,json; d=pymupdf.open(sys.argv[1]); print(json.dumps(bool(d.page_count and d.get_toc())))'
 p=subprocess.run([python,'-c',code,str(path)],capture_output=True,text=True,timeout=30)
 return p.returncode==0 and p.stdout.strip()=='true'

def episode_products(folder,stem,python):
 folder=pathlib.Path(folder)
 pdf=folder/(stem+'_带目录.pdf');full=folder/(stem+'_全集剧本.docx')
 singles=sorted((folder/'单集剧本').glob(stem+'_第*集.docx'))
 if not valid_docx(full) or not singles:return []
 if any(not valid_docx(p) or not re.fullmatch(re.escape(stem)+r'_第[0-9]+集\.docx',p.name) for p in singles):return []
 if heading_count(full)!=len(singles):return []
 if not pdf_has_toc(pdf,python):return []
 archive=folder/(stem+'_全集及单集Word剧本.zip')
 temporary=archive.with_suffix('.zip.tmp')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
  z.write(full,'全集剧本/'+full.name)
  for p in singles:z.write(p,'单集剧本/'+p.name)
 temporary.replace(archive)
 return [pdf,archive]

def instructions(contract):
 stem=contract['stem']
 if contract['kind']=='art':
  return f'只调用 screenplay-element-breakdown 直接读取原稿并按集按场提取，不调用 screenplay-episode-processor，不先拆单集 Word/PDF。技能中默认先分集的步骤被用户本次要求覆盖。最终只交付一个文件：{stem}_美术元素统计.xlsx。读取 Word 修订时使用接受修订后的视图，保留插入内容、排除已删除内容；如需预处理只在内部副本完成，不调用分集技能。中间 JSON/脚本仅留在内部。'
 return f'只调用 screenplay-episode-processor 一次性完成分集。用户不需要阶段确认。必须生成：{stem}_带目录.pdf（有可点击目录与书签）；{stem}_全集剧本.docx；单集剧本/{stem}_第N集.docx（N 为源稿阿拉伯集号，每集一份）。全集 Word 每集标题必须为 Heading 1；单集 Word 从该全集拆出。Word 输入阶段二使用 --no-pdf，不生成单集 PDF。桥接程序会将全集 Word 与所有单集 Word 自动打包为 {stem}_全集及单集Word剧本.zip，包内只放这些 Word 文件。最终仅回传带目录 PDF 和该 ZIP；不交付散装 Word、TXT、JSON 或其他压缩包。所有文件名必须保留上述原文件名，不能改用剧名。'
