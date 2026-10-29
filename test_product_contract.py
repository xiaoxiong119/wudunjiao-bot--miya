import unittest,tempfile,pathlib,zipfile,json
from unittest.mock import patch
import product_contract as p
import bridge as b

class Products(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.stem='测试剧本2'
 def tearDown(self):self.tmp.cleanup()
 def doc(self,path,headings=0):
  path.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>标题</w:t></w:r></w:p>'*headings)+'</w:body></w:document>')
 def setup_episodes(self):
  self.doc(self.root/(self.stem+'_全集剧本.docx'),2)
  for n in [34,35]:self.doc(self.root/'单集剧本'/(self.stem+f'_第{n}集.docx'))
  (self.root/(self.stem+'_带目录.pdf')).write_bytes(b'%PDF-')
 def test_word_only_zip_and_two_deliverables(self):
  self.setup_episodes();(self.root/'extra.txt').write_text('internal');(self.root/'extra.pdf').write_bytes(b'%PDF')
  with patch.object(p,'pdf_has_toc',return_value=True):files=p.episode_products(self.root,self.stem,'python')
  self.assertEqual([f.name for f in files],[self.stem+'_带目录.pdf',self.stem+'_全集及单集Word剧本.zip'])
  with zipfile.ZipFile(files[1]) as z:
   self.assertEqual(len(z.namelist()),3)
   self.assertTrue(all(name.endswith('.docx') for name in z.namelist()))
   self.assertTrue(all(self.stem in name for name in z.namelist()))
 def test_missing_episode_blocks_delivery(self):
  self.setup_episodes();(self.root/'单集剧本'/(self.stem+'_第35集.docx')).unlink()
  with patch.object(p,'pdf_has_toc',return_value=True):self.assertFalse(p.episode_products(self.root,self.stem,'python'))
 def test_pdf_without_toc_blocks_delivery(self):
  self.setup_episodes()
  with patch.object(p,'pdf_has_toc',return_value=False):self.assertFalse(p.episode_products(self.root,self.stem,'python'))
 def test_art_is_direct_and_uses_source_name(self):
  text=p.instructions({'kind':'art','stem':self.stem})
  self.assertIn('不调用 screenplay-episode-processor',text);self.assertIn('测试剧本2_美术元素统计.xlsx',text)
 def test_routing_maps_correct_skills(self):
  commands=b.registry()
  self.assertEqual(commands['/jbfj']['skills'],['screenplay-episode-processor'])
  self.assertEqual(commands['/mscf']['skills'],['screenplay-element-breakdown'])

if __name__=='__main__':unittest.main()
