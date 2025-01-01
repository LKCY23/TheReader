from asgiref.sync import async_to_sync
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
import json
from backend.setup_env import global_env
from clients.gemini_client import GeminiClient
from clients.client_pool import ClientPool
from .models import ApiKey, Document, Task, Project, Collection
from pipeline.document_pipeline import DocumentPipeline
import tempfile
import logging
import io
from pathlib import Path

logger = logging.getLogger(__name__)

# Create your views here.

def gemini_chat(request):
    json_data = json.loads(request.body)
    prompt = json_data.get('prompt')
    gemini_client: GeminiClient = global_env['gemini_client']
    response = gemini_client.chat_with_text(prompt)
    if 'error' in response:
        return JsonResponse({'error': response['error']}, status=500)
    return JsonResponse({'response': response['text']})

def gemini_chat_image(request):
    json_data = json.loads(request.body)
    prompt = json_data.get('prompt')
    image_data = json_data.get('image_data')
    image_type = json_data.get('image_type', 'base64')
    client_pool: ClientPool = global_env['gemini_client_pool']
    if not image_data:
        response = client_pool.execute_with_retry(GeminiClient.chat_with_text, prompt)
    else:
        response = client_pool.execute_with_retry(GeminiClient.chat_with_image, prompt, image_data, image_type)
    if 'error' in response:
        return JsonResponse({
            'error': response['error']
        }, status=500)
    return JsonResponse({
        'response': response['text']
    })

def add_api_key(request):
    json_data = json.loads(request.body)
    key = json_data.get('key')
    base_url = json_data.get('base_url', 'https://api.betterspace.top')
    # make test
    gemini_client = GeminiClient(api_key=key, base_url=base_url)
    response = gemini_client.chat_with_text('Hello, world!')
    if 'error' in response:
        return JsonResponse({'error': response['error']}, status=500)
    
    ApiKey.objects.create(key=key, base_url=base_url)
    return JsonResponse({'message': 'API key added successfully'})

def add_document(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    title = request.POST.get('title')
    file = request.FILES.get('file')
    collection_id = request.POST.get('collection_id')

    if not title or not file or not collection_id:
        return JsonResponse({'error': 'Missing title or file or collection_id'}, status=400)

    # 保存到临时文件，不要删除！
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
    
    document_pipeline: DocumentPipeline = global_env['document_pipeline']
    logger.debug(f"Adding document with title: {title} with file path: {temp_file_path}")
    task_id = document_pipeline.add_task(title, temp_file_path, collection_id)
    
    return JsonResponse({
        'message': '文档上传成功',
        'task_id': task_id
    })

def remove_document(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    json_data = json.loads(request.body)
    document_id = json_data.get('document_id')
    task_id = json_data.get('task_id')

    if not document_id and not task_id:
        return JsonResponse({'error': 'Missing document_id or task_id'}, status=400)
    
    if document_id:
        Document.objects.get(id=document_id).delete()
    if task_id:
        Task.objects.get(id=task_id).delete()
    return JsonResponse({'message': '文档删除成功'})

def list_documents(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    documents = Document.objects.all().order_by('-created_at')
    logger.debug(f"Listing documents: {documents}")
    type_map = {
        'image': '图片',
        'text': '文本',
        'pdf': 'PDF',
        'docx': 'DOCX',
        'pptx': 'PPTX'
    }
    documents_data = [{
        'id': doc.id,
        'title': doc.title,
        'created_at': doc.created_at.isoformat(),
        'file_type': type_map.get(doc.title.split('.')[-1], '未知'),
        'status': doc.linked_task.status,
        'url': f'/api/documents/view/{doc.id}.pdf'
    } for doc in documents]
    
    return JsonResponse({
        'documents': documents_data
    })

def get_document(request, document_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        document = Document.objects.get(id=document_id)
        english_sections = document.english_sections.all().first()
        chinese_sections = document.chinese_sections.all().first()
        
        document_data = {
            'id': document.id,
            'title': document.title,
            'created_at': document.created_at.isoformat(),
            'file_type': document.linked_task.metadata.get('file_type', '未知'),
            'status': document.linked_task.status,
            'english_sections': {
                'id': english_sections.id,
                'title': english_sections.title,
                'pages': english_sections.section.get('pages', []),
                'file_path': english_sections.linked_file_path
            },
            'chinese_sections': {
                'id': chinese_sections.id,
                'title': chinese_sections.title,
                'pages': chinese_sections.section.get('pages', []),
                'file_path': chinese_sections.linked_file_path
            }
        }
        
        return JsonResponse({
            'document': document_data
        })
    except Document.DoesNotExist:
        return JsonResponse({'error': '文档不存在'}, status=404)

def get_document_status(request, task_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        task = Task.objects.get(id=task_id)
        return JsonResponse({
            'status': task.status,
            'progress': task.progress,
            'error_message': task.error_message,
            'metadata': task.metadata
        })
    except Task.DoesNotExist:
        return JsonResponse({'error': '任务不存在'}, status=404)
    
def get_document_thumbnail(request, document_id):
    try:
        document = Document.objects.get(id=document_id)
        thumbnail_path = Path(document.linked_file_path) / "thumbnail.png"
        return FileResponse(open(thumbnail_path, 'rb'), content_type='image/png')
    except Document.DoesNotExist:
        return JsonResponse({'error': '文档不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取缩略图失败: {str(e)}")
        return JsonResponse({'error': '获取缩略图失败'}, status=500)

def view_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id)
        # 获取文档目录下的原始文件
        file_path = Path(document.linked_file_path) / document.title
        
        if not file_path.exists():
            return JsonResponse({'error': '文件不存在'}, status=404)
        
        # pdf object stream
        with open(file_path, 'rb') as file:
            pdf_stream = io.BytesIO(file.read())
        
        # 使用文档的实际标题作为下载文件名
        return FileResponse(
            pdf_stream, 
            filename=document.title,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="{document.title}"'}
        )
    except Document.DoesNotExist:
        return JsonResponse({'error': '文档不存在'}, status=404)
    except PermissionError:
        return JsonResponse({'error': '无法访问文件'}, status=403)
    except Exception as e:
        logger.error(f"查看文档失败: {str(e)}")
        return JsonResponse({'error': '查看文档失败'}, status=500)

def get_document_text_section(request, document_id):    
    document = Document.objects.get(id=document_id)
    english_sections = document.english_sections.all()
    chinese_sections = document.chinese_sections.all()
    return JsonResponse({
        'english_sections': [section.to_dict() for section in english_sections],
        'chinese_sections': [section.to_dict() for section in chinese_sections]
    })

def list_projects(request):
    if request.method != 'GET':
        return JsonResponse({'error': '方法不允许'}, status=405)
    
    projects = Project.objects.all().order_by('-created_at')
    projects_data = [{
        'id': project.id,
        'name': project.name,
        'created_at': project.created_at.isoformat(),
        'updated_at': project.updated_at.isoformat(),
        'collections_count': project.collections.count()
    } for project in projects]
    
    return JsonResponse({
        'projects': projects_data
    })

def create_project(request):
    if request.method != 'POST':
        return JsonResponse({'error': '方法不允许'}, status=405)
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        
        if not name:
            return JsonResponse({'error': '项目名称不能为空'}, status=400)
        
        project = Project.objects.create(name=name)
        
        return JsonResponse({
            'message': '项目创建成功',
            'project': {
                'id': project.id,
                'name': project.name,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat()
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        return JsonResponse({'error': '创建项目失败'}, status=500)

def get_project(request, project_id):
    if request.method != 'GET':
        return JsonResponse({'error': '方法不允许'}, status=405)
    
    try:
        project = Project.objects.get(id=project_id)
        collections = project.collections.all()
        
        collections_data = [{
            'id': collection.id,
            'name': collection.name,
            'created_at': collection.created_at.isoformat(),
            'updated_at': collection.updated_at.isoformat(),
            'documents_count': collection.documents.count()
        } for collection in collections]
        
        project_data = {
            'id': project.id,
            'name': project.name,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'collections': collections_data
        }
        
        return JsonResponse({
            'project': project_data
        })
    except Project.DoesNotExist:
        return JsonResponse({'error': '项目不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        return JsonResponse({'error': '获取项目详情失败'}, status=500)

def list_collections(request, project_id):
    if request.method != 'GET':
        return JsonResponse({'error': '方法不允许'}, status=405)
    
    try:
        project = Project.objects.get(id=project_id)
        collections = project.collections.all().order_by('-created_at')
        
        collections_data = [{
            'id': collection.id,
            'name': collection.name,
            'created_at': collection.created_at.isoformat(),
            'updated_at': collection.updated_at.isoformat(),
            'documents_count': collection.documents.count()
        } for collection in collections]
        
        return JsonResponse({
            'collections': collections_data
        })
    except Project.DoesNotExist:
        return JsonResponse({'error': '项目不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取集合列表失败: {str(e)}")
        return JsonResponse({'error': '获取集合列表失败'}, status=500)

def create_collection(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'error': '方法不允许'}, status=405)
    
    try:
        project = Project.objects.get(id=project_id)
        data = json.loads(request.body)
        name = data.get('name')
        
        if not name:
            return JsonResponse({'error': '集合名称不能为空'}, status=400)
        
        collection = Collection.objects.create(name=name)
        project.collections.add(collection)
        
        return JsonResponse({
            'message': '集合创建成功',
            'collection': {
                'id': collection.id,
                'name': collection.name,
                'created_at': collection.created_at.isoformat(),
                'updated_at': collection.updated_at.isoformat()
            }
        })
    except Project.DoesNotExist:
        return JsonResponse({'error': '项目不存在'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        logger.error(f"创建集合失败: {str(e)}")
        return JsonResponse({'error': '创建集合失败'}, status=500)

def get_collection(request, project_id, collection_id):
    
    try:
        project = Project.objects.get(id=project_id)
        collection = project.collections.get(id=collection_id)
        documents = collection.documents.all().order_by('-created_at')
        # 未完成的任务
        processing_tasks = Task.objects.filter(collection_id=collection_id, status__in=[Task.Status.PENDING, Task.Status.PREPROCESSING, Task.Status.EXTRACTING, Task.Status.TRANSLATING])
        processing_tasks_data = [{
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'progress': task.progress
        } for task in processing_tasks]
        
        documents_data = [{
            'id': doc.id,
            'title': doc.title,
            'created_at': doc.created_at.isoformat(),
            'updated_at': doc.updated_at.isoformat(),
            'status': doc.linked_task.status if hasattr(doc, 'linked_task') else None,
            'thumbnail_url': f'/api/documents/thumbnail/{doc.id}.png'
        } for doc in documents]
        
        collection_data = {
            'id': collection.id,
            'name': collection.name,
            'created_at': collection.created_at.isoformat(),
            'updated_at': collection.updated_at.isoformat(),
            'documents': documents_data,
            'processing_tasks': processing_tasks_data
        }
        
        return JsonResponse({
            'collection': collection_data
        })
    except Project.DoesNotExist:
        return JsonResponse({'error': '项目不存在'}, status=404)
    except Collection.DoesNotExist:
        return JsonResponse({'error': '集合不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取集合详情失败: {str(e)}")
        return JsonResponse({'error': '获取集合详情失败'}, status=500)
