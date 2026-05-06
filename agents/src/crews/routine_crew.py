from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from src.tools.rag_tool import RAGQueryTool
from src.settings.config import CrewSettings
from langfuse import observe

settings = CrewSettings()

llm = LLM(
    model=settings.model_name,
    temperature=0.1,
    api_base=settings.model_api_base,
    api_key=settings.model_api_key
)

rag_tool = RAGQueryTool()

@CrewBase
class RoutineArchitectCrew():
    """Crew for building skincare routines"""

    agents_config = 'config/routine_agents.yaml'
    tasks_config = 'config/routine_tasks.yaml'

    @agent
    def routine_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['routine_architect'],
            verbose=True,
            llm=llm,
            tools=[rag_tool],
            allow_delegation=False
        )

    @task
    def build_routine_task(self) -> Task:
        return Task(
            config=self.tasks_config['build_routine_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.routine_architect()],
            tasks=[self.build_routine_task()],
            process=Process.sequential,
            verbose=True,
        )
        
    @observe(name="Routine Run")
    def run_monitored(self, inputs: dict):
        return self.crew().kickoff(inputs=inputs)