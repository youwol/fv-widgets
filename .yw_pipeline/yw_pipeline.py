from typing import List

from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models import IPipelineFactory
from youwol.environment.models_project import JsBundle, PipelineStep, FileListing, Artifact, Pipeline, Flow
from youwol.pipelines.pipeline_typescript_weback_npm import Paths, get_dependencies, create_sub_pipelines_publish
from youwol.pipelines.publish_cdn import PublishCdnLocalStep, PublishCdnRemoteStep
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json


class BuildStep(PipelineStep):
    id: str = "build"
    run: str = "yarn build-css"
    sources: FileListing = FileListing(
        include=[Paths.package_json_file, "webpack.config.js", "src/sass"],
        ignore=[Paths.auto_generated_file, "**/.*/*"]
    )

    artifacts: List[Artifact] = [
        Artifact(
            id='dist',
            files=FileListing(
                include=[Paths.package_json_file, "dist"]
            ),
            links=[]
        )
    ]


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, env: YouwolEnvironment, context: Context):

        publish_remote_steps, dags = await create_sub_pipelines_publish(start_step="publish-local", context=context)

        async with context.start(action="pipeline") as ctx:
            await ctx.info(text="Instantiate pipeline")
            return Pipeline(
                target=JsBundle(),
                tags=["flux-view", "css", "sass"],
                projectName=lambda path: parse_json(path / Paths.package_json_file)["name"],
                projectVersion=lambda path: parse_json(path / Paths.package_json_file)["version"],
                dependencies=lambda project, _ctx: get_dependencies(project),
                steps=[
                    BuildStep(),
                    PublishCdnLocalStep(packagedArtifacts=['dist']),
                    *publish_remote_steps
                ],
                flows=[
                    Flow(
                        name="prod",
                        dag=[
                            "build > publish-local",
                            *dags
                        ]
                    )
                ]
            )
