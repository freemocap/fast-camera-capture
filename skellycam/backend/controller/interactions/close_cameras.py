# from typing import Optional
#
# from skellycam.backend.controller.controller import Controller
#
# class CloseCamerasRequest(BaseRequest):
#     pass
#
#
# class CloseCamerasResponse(BaseModel):
#     pass
#
#
# class CloseCamerasCommand(BaseCommand):
#     async def execute(self, controller: "Controller", **kwargs) -> CloseCamerasResponse:
#         await controller.camera_group_manager.close()
#         return CloseCamerasResponse(success=True)
#
#
# class CloseCamerasInteraction(BaseInteraction):
#     request: CloseCamerasRequest
#     command: Optional[CloseCamerasCommand]
#     response: Optional[CloseCamerasResponse]
#
#     @classmethod
#     def as_request(cls, **kwargs):
#         return cls(request=CloseCamerasRequest.create(**kwargs))
#
#     def execute_command(self, controller: "Controller") -> CloseCamerasResponse:
#         self.command = CloseCamerasCommand()
#         self.response = self.command.execute(controller)
#         return self.response
