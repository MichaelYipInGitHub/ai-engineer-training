# article_mcp_server.py
import json
import time

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ArticleCreator")


@mcp.tool()
def research_topic(topic: str) -> str:
    """对指定主题进行研究，收集相关信息"""
    # 模拟研究过程 - 实际应用中可接入搜索引擎API
    research_data = {
        "AI Agent": {
            "definition": "AI代理是能够感知环境、做出决策并执行行动的人工智能系统",
            "applications": ["自动化客服", "内容生成", "数据分析", "智能助手"],
            "trends": ["多智能体协作", "自主决策", "专业化发展"],
            "challenges": ["安全性", "伦理问题", "技术复杂度"]
        },
        "机器学习": {
            "definition": "让计算机通过数据学习并改进性能的技术",
            "types": ["监督学习", "无监督学习", "强化学习"],
            "applications": ["预测分析", "图像识别", "自然语言处理"]
        }
    }

    topic_data = research_data.get(topic, {
        "definition": f"{topic}是一个重要的技术领域，正在快速发展。",
        "key_points": ["技术革新", "应用广泛", "未来发展潜力大"],
        "status": "活跃研究领域"
    })

    return json.dumps(topic_data, ensure_ascii=False, indent=2)


@mcp.tool()
def write_article_outline(topic: str, research_data: str) -> str:
    """根据研究数据撰写文章大纲"""
    research = json.loads(research_data)

    outline = {
        "title": f"关于{topic}的深度分析文章",
        "sections": [
            {
                "title": "引言",
                "content": f"介绍{topic}的基本概念和重要性"
            },
            {
                "title": "核心概念",
                "content": research.get("definition", "核心概念阐述")
            },
            {
                "title": "应用领域",
                "content": "，".join(research.get("applications", ["各个领域"]))
            },
            {
                "title": "发展趋势",
                "content": "，".join(research.get("trends", ["持续发展"]))
            },
            {
                "title": "挑战与展望",
                "content": "总结当前面临的挑战和未来发展方向"
            }
        ]
    }

    return json.dumps(outline, ensure_ascii=False, indent=2)


@mcp.tool()
def draft_article_section(section_title: str, content_guidance: str) -> str:
    """根据大纲草拟文章章节内容"""
    # 模拟章节内容生成
    section_templates = {
        "引言": f"""
            随着人工智能技术的快速发展，{content_guidance}已经成为当今科技领域的热点话题。
            本文将从多个角度深入分析这一重要技术，探讨其应用前景和发展趋势。
            """,
        "核心概念": f"""
            从技术层面来看，{content_guidance}代表了人工智能发展的重要方向。
            这一概念的核心在于创建能够自主学习和决策的智能系统。
            """,
        "应用领域": f"""
            在实际应用中，{content_guidance}已经展现出巨大的价值。
            这些应用不仅提高了效率，还创造了新的商业模式和用户体验。
            """,
        "发展趋势": f"""
            展望未来，{content_guidance}将继续推动技术创新。
            行业专家预测，这一领域将在未来几年内保持高速增长。
            """,
        "挑战与展望": f"""
            尽管前景广阔，{content_guidance}仍面临诸多挑战。
            需要在技术创新与伦理规范之间找到平衡点。
            """
    }

    return section_templates.get(section_title, f"""
        # {section_title}
        
        {content_guidance}
        
        这一部分需要进一步展开和详细阐述，以提供全面的分析视角。
        """)


@mcp.tool()
def review_article_content(content: str, criteria: str = "专业性,逻辑性,可读性") -> str:
    """审核文章内容质量"""
    review_criteria = criteria.split(",")

    review_results = {}
    for criterion in review_criteria:
        if criterion == "专业性":
            review_results[criterion] = "内容专业，术语使用准确"
        elif criterion == "逻辑性":
            review_results[criterion] = "逻辑清晰，结构合理"
        elif criterion == "可读性":
            review_results[criterion] = "语言流畅，易于理解"
        else:
            review_results[criterion] = "符合基本要求"

    suggestions = [
        "建议增加具体案例说明",
        "可以补充最新数据支持",
        "考虑添加图表辅助说明"
    ]

    review_report = {
        "overall_score": 85,
        "criteria_evaluation": review_results,
        "suggestions": suggestions,
        "verdict": "内容质量良好，建议进行适度润色"
    }

    return json.dumps(review_report, ensure_ascii=False, indent=2)


@mcp.tool()
def polish_article_content(content: str, polish_type: str = "全面润色") -> str:
    """对文章内容进行润色优化"""

    polish_strategies = {
        "全面润色": """
            优化语言表达，提升专业性
            调整句式结构，增强可读性
            统一术语使用，确保一致性
            """,
        "语言优化": """
            精简冗余表述
            增强逻辑连接
            提升文采表达
            """,
        "结构优化": """
            调整段落顺序
            优化过渡衔接
            强化重点突出
            """
    }

    strategy = polish_strategies.get(polish_type, "标准润色处理")

    polished_content = f"""
        【润色说明】
        执行了{polish_type}处理，主要改进方向：
        {strategy}
        
        【润色后内容】
        {content}
        
        【改进说明】
        - 优化了语言表达的准确性和流畅度
        - 增强了内容的逻辑性和连贯性  
        - 提升了文章的专业性和可读性
        """

    return polished_content


@mcp.tool()
def assemble_final_article(sections: list, title: str) -> str:
    """将各个章节组装成最终文章"""

    article = f"# {title}\n\n"
    article += "*本文由多智能体协作系统自动生成*\n\n"

    for i, section in enumerate(sections, 1):
        if isinstance(section, dict):
            section_content = section.get('content', '')
            section_title = section.get('title', f'第{i}部分')
        else:
            section_content = section
            section_title = f'第{i}部分'

        article += f"## {section_title}\n\n"
        article += f"{section_content}\n\n"

    article += "---\n"
    article += "*生成时间: {}*\n".format(time.strftime("%Y-%m-%d %H:%M:%S"))
    article += "*字数统计: 约{}字*".format(len(article) // 3)

    return article


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
