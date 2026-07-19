"""Documents and workspaces API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.dependencies import get_authenticated_context, get_service, require_roles
from app.core.context import RequestContext, UserRole
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.documents.schemas import (
    DocumentResponse,
    DocumentUploadResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.modules.documents.services import DocumentService, WorkspaceService

documents_router = APIRouter(prefix="/documents", tags=["Documents"])
workspaces_router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# Workspace routes

@workspaces_router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OWNER))],
)
async def create_workspace(
    data: WorkspaceCreate,
    service: WorkspaceService = Depends(get_service(WorkspaceService)),
):
    workspace = await service.create(data)
    await service.uow.commit()
    return workspace


@workspaces_router.get("", response_model=PaginatedResponse[WorkspaceResponse])
async def list_workspaces(
    pagination: PaginationParams = Depends(),
    service: WorkspaceService = Depends(get_service(WorkspaceService)),
):
    items, total = await service.list(pagination)
    return PaginatedResponse.create(items, total, pagination)


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    service: WorkspaceService = Depends(get_service(WorkspaceService)),
):
    return await service.get(workspace_id)


@workspaces_router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OWNER))],
)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    service: WorkspaceService = Depends(get_service(WorkspaceService)),
):
    workspace = await service.update(workspace_id, data)
    await service.uow.commit()
    return workspace


# Document routes

@documents_router.post(
    "/upload/{workspace_id}",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    context: RequestContext = Depends(get_authenticated_context),
    service: DocumentService = Depends(get_service(DocumentService)),
):
    content = await file.read()
    document = await service.upload(
        workspace_id=workspace_id,
        filename=file.filename or "upload.bin",
        content=content,
        content_type=file.content_type,
        storage=request.app.state.storage,
        context=context,
    )
    await service.uow.commit()
    return DocumentUploadResponse(document=document)


@documents_router.get(
    "/workspace/{workspace_id}",
    response_model=PaginatedResponse[DocumentResponse],
)
async def list_documents(
    workspace_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    service: DocumentService = Depends(get_service(DocumentService)),
):
    items, total = await service.list_by_workspace(workspace_id, pagination)
    return PaginatedResponse.create(items, total, pagination)


@documents_router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_service(DocumentService)),
):
    return await service.get(document_id)


@documents_router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OWNER))],
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    service: DocumentService = Depends(get_service(DocumentService)),
):
    await service.delete(document_id, request.app.state.storage)
    await service.uow.commit()
