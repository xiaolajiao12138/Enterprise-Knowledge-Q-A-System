import os
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册中文字体
font_path = "C:/Windows/Fonts/simhei.ttf"
pdfmetrics.registerFont(TTFont("SimHei", font_path))

target_dir = r"C:\Users\Administrator\Desktop\企业知识问答测试文档"
os.makedirs(target_dir, exist_ok=True)

docs = [
    {
        "filename": "企业员工考勤与休假管理制度",
        "title": "企业员工考勤与休假管理制度（2026年正式版）",
        "sections": [
            ("第一章 工作时间与考勤管理", [
                "1. 标准工时制：公司实行每周 5 天工作制（周一至周五）。每日标准工作时间为 8 小时，具体上下班时间为：上午 09:00 至 12:00，下午 13:30 至 18:30。午休时间为 12:00 至 13:30。",
                "2. 打卡规范：所有在职员工须通过企业微信或办公区门禁机完成每日两次打卡（上班卡与下班卡）。",
                "3. 弹性打卡福利：为缓解早晚交通拥堵，公司提供 30 分钟弹性时间（上午 09:00 - 09:30 到岗，相应下班时间顺延至 18:30 - 19:00 即可）。",
                "4. 迟到与早退界定：超过规定上班时间 30 分钟以内（含弹性后）到达且未提前报备的，视为迟到；迟到 30 分钟以上 2 小时以内视为旷工半天；每月每位员工享有 3 次 10 分钟以内的免扣款迟到机会。"
            ]),
            ("第二章 休假类型与申请流程", [
                "1. 法定年休假：累计工作满 1 年不满 10 年的，年休假 5 天；已满 10 年不满 20 年的，年休假 10 天；已满 20 年的，年休假 15 天。公司额外为司龄满 1 年的员工每年发放 1 天福利司龄假，上限累计不超过 5 天。",
                "2. 带薪病假：每位转正员工每年享有 5 天全额带薪病假。申请病假须提供二级及以上公立医院出具的就诊记录或病休证明，1 天以内可由直属主管审批，超过 3 天须由部门总监及人事负责人审批。",
                "3. 婚假与产假：符合法定结婚年龄的员工可享受 3 天带薪婚假；女员工顺产享受产假 158 天（含难产及多胞胎递增天数），男员工享受陪产假 15 天。",
                "4. 事假：事假为无薪假，按实际缺勤天数折算扣减当月基本工资，单次事假原则上不得超过 5 个工作日。"
            ]),
            ("第三章 加班与调休规定", [
                "1. 加班申请：因业务紧急需要加班的，员工须提前在 OA 提交加班申请单，工作日加班需满 1 小时方可起计。",
                "2. 调休机制：工作日及周末加班优先以 1:1 折算为调休假，调休有效期为自然年内有效，逾期未调休将按国家法定标准核算加班费发放。"
            ])
        ]
    },
    {
        "filename": "企业财务报销与差旅管理规定",
        "title": "企业财务报销与差旅管理规定（2026年正式版）",
        "sections": [
            ("第一章 总则与出差审批", [
                "第一条 为规范公司内部各项财务开支，合理控制运营成本，提高资金使用效率，特制定本管理规定。",
                "第二条 出差申请流程：员工因公出差前，必须提前至少 1 个工作日在 OA 系统提交《因公出差申请表》，详细注明出差事由、行程目的地、起止时间及预计费用，经直属主管及部门负责人审批通过后方可执行。"
            ]),
            ("第二章 交通费标准与订票规范", [
                "第三条 交通工具选择：员工出差应本着安全、经济、快捷的原则。出差距离在 800 公里以内的，原则上乘坐高铁/动车二等座或普通火车硬卧；出差单程飞行时间超过 4 小时或跨省长途行程，可选择民航班机经济舱。",
                "第四条 市内交通：市内交通优先乘坐地铁、公交或网约车普通车型，严禁违规报销豪华车型或出租车过桥过路不合规附加费。"
            ]),
            ("第三章 住宿标准与餐饮补贴", [
                "第五条 住宿限额标准：一线城市（北京、上海、广州、深圳）每人每天不超过 500 元；新一线城市及重点省会城市每人每天不超过 350 元；其他二三线及以下城市每人每天不超过 260 元。总监及以上管理人员标准可上浮 30%。",
                "第六条 出差伙食补贴：出差期间餐饮补贴按照每人每天 100 元包干发放，按实际出差自然天数核算，无需提供餐饮发票凭证。"
            ]),
            ("第四章 发票合规与报销时限", [
                "第七条 报销凭证要求：所有报销发票抬头必须为公司全称，纳税人识别号必须准确无误。严禁虚开、借用或涂改发票。",
                "第八条 报销截止时效：员工完成出差返回公司后，须在 10 个工作日内完成 OA 报销审批及纸质单据投递。当月发生的常规费用最迟须在次月 10 日前报销完毕，跨年发票逾期不予受理。"
            ])
        ]
    },
    {
        "filename": "企业信息安全与数据保密规范",
        "title": "企业信息安全与数据保密管理规范（2026年正式版）",
        "sections": [
            ("第一章 账户与密码安全管理", [
                "1. 强密码策略：所有办公系统、统一认证平台（SSO）、代码仓库和云控制台密码必须满足以下复杂度要求：长度不少于 12 位字符；包含大写字母、小写字母、数字及特殊符号（如 !@#$%^&*）；密码有效期最长为 90 天，到期系统强制提示修改，且最近 3 次使用过的历史密码不得重复使用。",
                "2. 多因子认证（MFA）：所有包含客户隐私数据、财务信息或核心生产环境的管理平台必须开启手机动态令牌（TOTP）或企业微信扫码二次认证。",
                "3. 账户借用禁令：员工账号仅限本人使用，严禁转借他人或与同事共享。离开办公工位时必须执行锁屏（快捷键 Win + L 或 Mac Control + Command + Q）。"
            ]),
            ("第二章 数据分级与外传合规", [
                "1. 数据密级分类：公开级（L1）：对外发布的宣传材料、官网招聘信息；内部级（L2）：公司内部通知、通用流程制度、内部培训资料；秘密级（L3）：未公开财务报表、产品核心架构源码、重要客户商务合同；机密级（L4）：核心商业机密、战略并购规划、用户高敏感隐私数据。",
                "2. 代码与文档外传限制：严禁将公司内部任何源代码、配置文件、数据库备份文件上传至 GitHub 公开仓库、Gitee、百度网盘或任何第三方公网存储；严禁将包含客户个人信息（身份证、手机号、银行卡）的数据发送至非公司域名的外部个人邮箱。"
            ]),
            ("第三章 知识库与本地 AI 使用准则", [
                "1. 私有化 RAG 平台使用原则：本企业内部知识库平台已部署在公司受控内网，上传知识库的所有文档严禁包含机密级（L4）的核心用户敏感隐私或未解密的财务核心凭证。",
                "2. 大模型选型规范：涉及企业内部 L2、L3 级文档的问答推理，必须使用企业本地私有化部署的大模型，严禁将内部敏感片段发送给未签订企业级数据保密协议的公网消费级大模型；知识库系统检索引用的文档片段只在内网流转，禁止截屏转发至外部社交软件。"
            ])
        ]
    }
]

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontName="SimHei",
    fontSize=18,
    leading=24,
    alignment=1,
    spaceAfter=15
)
h2_style = ParagraphStyle(
    "DocH2",
    parent=styles["Heading2"],
    fontName="SimHei",
    fontSize=13,
    leading=18,
    spaceBefore=12,
    spaceAfter=6,
    textColor="#1e3a8a"
)
body_style = ParagraphStyle(
    "DocBody",
    parent=styles["Normal"],
    fontName="SimHei",
    fontSize=10.5,
    leading=16,
    spaceAfter=6,
    firstLineIndent=20
)

for item in docs:
    fname = item["filename"]
    
    # 1. 生成 PDF
    pdf_path = os.path.join(target_dir, f"{fname}.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    story = [Paragraph(item["title"], title_style), Spacer(1, 10)]
    for sec_title, sec_paragraphs in item["sections"]:
        story.append(Paragraph(sec_title, h2_style))
        for p_text in sec_paragraphs:
            story.append(Paragraph(p_text, body_style))
    doc.build(story)
    
    # 2. 生成 Markdown
    md_path = os.path.join(target_dir, f"{fname}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {item['title']}\n\n")
        for sec_title, sec_paragraphs in item["sections"]:
            f.write(f"## {sec_title}\n\n")
            for p_text in sec_paragraphs:
                f.write(f"{p_text}\n\n")
                
    # 3. 生成 TXT
    txt_path = os.path.join(target_dir, f"{fname}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"【{item['title']}】\n\n")
        for sec_title, sec_paragraphs in item["sections"]:
            f.write(f"=== {sec_title} ===\n")
            for p_text in sec_paragraphs:
                f.write(f"{p_text}\n")
            f.write("\n")

print("All documents generated successfully in target directory!")
