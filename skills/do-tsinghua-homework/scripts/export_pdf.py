#!/usr/bin/env python3
"""Export a local Markdown report with embedded Chinese fonts and image previews."""
import argparse
import html
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak, KeepTogether,
    Table, TableStyle, Preformatted,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from PIL import Image as PILImage


def fonts(args):
    defaults = {
        'Song': ('/System/Library/Fonts/Supplemental/Songti.ttc', 6),
        'SongBold': ('/System/Library/Fonts/Supplemental/Songti.ttc', 1),
        'Hei': ('/System/Library/Fonts/STHeiti Medium.ttc', 1),
        'Roman': ('/System/Library/Fonts/Supplemental/Times New Roman.ttf', 0),
        'RomanBold': ('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf', 0),
    }
    if args.chinese_font:
        defaults['Song'] = (args.chinese_font, args.chinese_index)
        defaults['SongBold'] = (args.chinese_bold or args.chinese_font, 0 if args.chinese_bold else args.chinese_index)
    if args.heading_font:
        defaults['Hei'] = (args.heading_font, args.heading_index)
    if args.latin_font:
        defaults['Roman'] = (args.latin_font, 0)
        defaults['RomanBold'] = (args.latin_bold or args.latin_font, 0)
    for name, (path, index) in defaults.items():
        if not Path(path).is_file():
            raise ValueError(f'字体不存在：{path}；请指定对应字体参数。')
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))


def plain_runs(text, bold=False, italic=False, heading=False):
    chinese = 'Hei' if heading else ('SongBold' if bold else 'Song')
    roman = 'RomanBold' if bold or heading else 'Roman'
    out = []
    for part in re.split(r'([\x20-\x7e]+)', text):
        if not part:
            continue
        face = roman if re.fullmatch(r'[\x20-\x7e]+', part) else chinese
        # Fail rather than ship a blank square for a missing CJK glyph.
        cmap = pdfmetrics.getFont(face).face.charToGlyph
        absent = {c for c in part if not c.isspace() and ord(c) not in cmap}
        if absent:
            raise ValueError(f'字体 {face} 缺少字符：{"".join(sorted(absent))}')
        out.append(f'<font name="{face}">{html.escape(part)}</font>')
    result = ''.join(out)
    return f'<i>{result}</i>' if italic else result


def inline(text, heading=False):
    pattern = r'(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^\)\n]+\))'
    result = []
    for part in re.split(pattern, text):
        if not part:
            continue
        if part.startswith('`') and part.endswith('`'):
            content = part[1:-1]
            if content.isascii():
                result.append('<font name="Courier">'+html.escape(content)+'</font>')
            else:
                result.append(plain_runs(content, heading=heading))
        elif part.startswith('**') and part.endswith('**'):
            result.append(plain_runs(part[2:-2], bold=True, heading=heading))
        elif part.startswith('*') and part.endswith('*'):
            result.append(plain_runs(part[1:-1], italic=True, heading=heading))
        elif re.fullmatch(r'\[[^\]\n]+\]\([^\)\n]+\)', part):
            match = re.fullmatch(r'\[([^\]]+)\]\((.+)\)', part)
            label, url = match.groups()
            if urlparse(url).scheme in {'https', 'http', 'mailto'}:
                result.append(f'<link href="{html.escape(url, quote=True)}">{plain_runs(label)}</link>')
            else:
                result.append(plain_runs(label))
        else:
            result.append(plain_runs(part, heading=heading))
    return ''.join(result)


def parse(source):
    """A bounded Markdown subset; preserve content and reject unsupported blocks."""
    lines = source.splitlines()
    blocks = []
    i = 0
    special = r'^(#{1,6} |!\[|```|~~~|<!-- pagebreak -->|[-*+] |\d+[.)] |\|)'
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if lines[i].startswith(('  - ', '  * ', '    - ', '    * ')):
            raise ValueError('遇到多级列表；请选择支持完整 Markdown 的转换方式。')
        if line.startswith(('```', '~~~')):
            fence = line[:3]
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code.append(lines[i]); i += 1
            if i == len(lines):
                raise ValueError('代码块缺少结束围栏。')
            blocks.append(('code', '\n'.join(code)))
        elif line == '<!-- pagebreak -->':
            blocks.append(('break', None))
        elif line.startswith('<') or line.startswith('>') or re.match(r'^(\$\$|\\\[)', line):
            raise ValueError(f'暂不支持此块：{line[:70]}')
        elif re.match(r'^#{1,6} ', line):
            match = re.match(r'^(#{1,6}) (.*)$', line)
            blocks.append(('heading', (len(match[1]), match[2])))
        elif line.startswith('!['):
            match = re.fullmatch(r'!\[([^\]]*)\]\((.+)\)', line)
            if not match:
                raise ValueError('图片请使用单独一行的 ![说明](路径) 格式。')
            target = match[2].strip()
            # Optional Markdown image title, or <path with spaces>.
            target = re.sub(r'\s+"[^"]*"$', '', target)
            if target.startswith('<') and target.endswith('>'):
                target = target[1:-1]
            blocks.append(('image', target))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            if len({len(row) for row in rows}) != 1:
                raise ValueError('表格各行的列数不一致；转义竖线表格需使用其他转换器。')
            blocks.append(('table', rows))
        elif re.match(r'^([-*+] |\d+[.)] )', line):
            blocks.append(('list', line))
        elif line in {'---', '***', '___'}:
            raise ValueError('遇到分隔线或 YAML 前言；请使用适合完整 Markdown 的转换方式。')
        else:
            paragraph = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(special, lines[i].strip()):
                if lines[i].strip().startswith(('<', '>', '$$')):
                    raise ValueError('段落中有不支持的 HTML、引用或公式块。')
                paragraph.append(lines[i].strip()); i += 1
            i -= 1
            text = '\n'.join(paragraph)
            if '![' in text or '$' in text or '\\(' in text:
                raise ValueError('行内图片或公式需使用其他转换方式。')
            blocks.append(('paragraph', text))
        i += 1
    return blocks


def export(args):
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if source == output:
        raise ValueError('输出路径不能覆盖 Markdown 源文件。')
    blocks = parse(source.read_text(encoding='utf-8'))
    fonts(args)
    size = args.body_size or (11 if args.compact else 12)
    leading = args.leading or (18 if args.compact else 22)
    width, height = (841.89, 595.28) if args.landscape else (595.28, 841.89)
    available_width = width - 104
    available_height = height - 93
    body = ParagraphStyle('body',fontName='Song',fontSize=size,leading=leading,
                          firstLineIndent=size*2,spaceAfter=12,wordWrap='CJK')
    small = ParagraphStyle('short',parent=body,fontSize=11,leading=17,
                           firstLineIndent=0,spaceAfter=8)
    caption = ParagraphStyle('caption',parent=small,fontSize=9.5,leading=15,spaceBefore=9)
    story = []
    i = 0
    image_count = 0
    while i < len(blocks):
        kind, value = blocks[i]
        if kind == 'heading':
            level, text = value
            if level == 1 and args.break_h1 and story and not isinstance(story[-1],PageBreak):
                story.append(PageBreak())
            style = ParagraphStyle('h'+str(level),fontName='Hei',fontSize=17 if level==1 else 12,
                                   leading=25 if level==1 else 19,spaceBefore=0 if level==1 else 4,
                                   spaceAfter=22 if level==1 else 9,keepWithNext=True,wordWrap='CJK')
            story.append(Paragraph(inline(text,heading=True),style))
        elif kind == 'break':
            if story and not isinstance(story[-1],PageBreak):story.append(PageBreak())
        elif kind == 'paragraph' and re.match(r'^（[0-9０-９]+）',value):
            parts = [value]
            while i+1 < len(blocks) and blocks[i+1][0]=='paragraph' and not re.match(r'^（[0-9０-９]+）',blocks[i+1][1]):
                i += 1; parts.append(blocks[i][1])
            story.append(Paragraph('<br/>'.join(inline(p) for p in parts),small))
        elif kind == 'image':
            if urlparse(value).scheme and not re.match(r'^[A-Za-z]:',value):
                raise ValueError('图片必须是本地文件；请使用已有本地图，不自动下载远程图片。')
            path = Path(unquote(value)).expanduser()
            if not path.is_absolute():path = source.parent/path
            path = path.resolve()
            if not path.is_file():raise ValueError(f'图片不存在：{path}')
            with PILImage.open(path) as pic:
                w,h=pic.size
            caption_flow = None
            if i+1<len(blocks) and blocks[i+1][0]=='paragraph' and re.match(r'^(图\s*\d|Figure\s*\d|Fig\.\s*\d)',blocks[i+1][1],re.I):
                i+=1;caption_flow=Paragraph(inline(blocks[i][1]),caption)
            reserve = (caption_flow.wrap(available_width,available_height)[1]+17) if caption_flow else 8
            maximum = min(args.image_max_height or available_height*.76,available_height-reserve)
            scale = min(available_width/w,maximum/h)
            image = Image(str(path),width=w*scale,height=h*scale,mask='auto')
            dpi = 72/scale
            if dpi<110:print(f'图片清晰度提示：{path.name} 约 {dpi:.0f} dpi，请检查实际可读性。')
            group=[image]
            if caption_flow:group.append(caption_flow)
            story.append(KeepTogether(group));image_count+=1
        elif kind == 'code':
            face='Courier' if value.isascii() else 'Song'
            font_size=9
            longest=max((pdfmetrics.stringWidth(line,face,font_size) for line in value.splitlines()),default=0)
            if longest>available_width:
                raise ValueError('代码行超过页宽，请手动换行或使用横向页面。')
            style=ParagraphStyle('code',fontName=face,fontSize=font_size,leading=13,spaceAfter=10)
            story.append(Preformatted(value,style))
        elif kind == 'table':
            rows=[[Paragraph(inline(cell),caption) for cell in row] for row in value]
            table=Table(rows,colWidths=[available_width/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0f0f0')),
                ('LINEBELOW',(0,0),(-1,0),.5,colors.grey),('LINEBELOW',(0,-1),(-1,-1),.5,colors.grey),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,10)])
        else:
            if kind=='list':
                value=re.sub(r'^[-*+] ', '• ', value)
            style=small if kind=='list' else caption if re.match(r'^图\s*\d',value) else body
            story.append(Paragraph(inline(value).replace('\n','<br/>'),style))
        i+=1
    output.parent.mkdir(parents=True,exist_ok=True)
    def footer(canvas,doc):
        canvas.setFont('Roman',9);canvas.setFillColorRGB(.42,.42,.42)
        canvas.drawCentredString(width/2,28,str(doc.page))
    doc=SimpleDocTemplate(str(output),pagesize=(width,height),leftMargin=52,rightMargin=52,
                          topMargin=48,bottomMargin=45,title=source.stem)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(f'已导出：{output}；嵌入宋体/黑体；图片 {image_count} 张。')
    if args.render_dir:
        import pypdfium2
        directory=Path(args.render_dir).expanduser().resolve();directory.mkdir(parents=True,exist_ok=True)
        pdf=pypdfium2.PdfDocument(str(output))
        for number,page in enumerate(pdf,1):
            bitmap=page.render(scale=1.5)
            bitmap.to_pil().save(directory/f'page-{number:02}.png');bitmap.close();page.close()
        print(f'页数：{len(pdf)}；预览：{directory}');pdf.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('output')
    parser.add_argument('--break-h1',action='store_true')
    parser.add_argument('--compact',action='store_true')
    parser.add_argument('--landscape',action='store_true')
    parser.add_argument('--body-size',type=float);parser.add_argument('--leading',type=float)
    parser.add_argument('--image-max-height',type=float,help='Image height limit in PDF points')
    parser.add_argument('--render-dir')
    parser.add_argument('--chinese-font');parser.add_argument('--chinese-index',type=int,default=0)
    parser.add_argument('--chinese-bold');parser.add_argument('--heading-font')
    parser.add_argument('--heading-index',type=int,default=0)
    parser.add_argument('--latin-font');parser.add_argument('--latin-bold')
    args=parser.parse_args()
    for key in ['body_size','leading','image_max_height']:
        if getattr(args,key) is not None and getattr(args,key)<=0:parser.error(f'{key} 必须为正数')
    try:export(args)
    except (ValueError,FileNotFoundError) as error:parser.exit(1,f'导出失败：{error}\n')

if __name__=='__main__':main()
