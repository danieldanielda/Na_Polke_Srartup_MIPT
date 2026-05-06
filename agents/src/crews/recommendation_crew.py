# src/crews/recommendation_crew.py
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from langfuse import observe

from src.tools.rag_tool import RAGQueryTool
from src.settings.config import CrewSettings

settings = CrewSettings()

llm = LLM(
    model=settings.model_name,
    temperature=0.2,
    api_base=settings.model_api_base,
    api_key=settings.model_api_key
)

rag_tool = RAGQueryTool()

@CrewBase
class RecommendationCrew():
    agents_config = 'config/rec_agents.yaml'
    tasks_config = 'config/rec_tasks.yaml'

    @agent
    def recommendation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['recommendation_agent'],
            verbose=True,
            llm=llm,
            tools=[rag_tool],
        )

    @task
    def recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config['recommendation_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.recommendation_agent()],
            tasks=[self.recommendation_task()],
            process=Process.sequential,
            verbose=True,
        )

    @observe(name="Recommendation Crew Run")
    def run_monitored(self, inputs: dict):
        return self.crew().kickoff(inputs=inputs)