"""
Google API Integration Service
Handles Google Docs, Google Forms, and other Google Workspace integrations
"""
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from flask import current_app
import json
import tempfile
import requests


class GoogleAPIService:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/forms.body'
        ]
        self.creds = None
        
    def get_credentials(self):
        """Get valid Google API credentials"""
        # In production, you'd store credentials securely
        # For now, we'll return None to indicate setup needed
        if not current_app.config.get('GOOGLE_CREDENTIALS_JSON'):
            return None
            
        # Load credentials from config
        creds_json = current_app.config.get('GOOGLE_CREDENTIALS_JSON')
        if creds_json:
            if isinstance(creds_json, str):
                creds_json = json.loads(creds_json)
            
            # Create credentials object
            creds = Credentials.from_authorized_user_info(creds_json, self.scopes)
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
            return creds
            
        return None

    def create_document(self, title, content):
        """Create a Google Doc with the given title and content"""
        creds = self.get_credentials()
        if not creds:
            return {'error': 'Google credentials not configured'}
        
        try:
            service = build('docs', 'v1', credentials=creds)
            
            # Create the document
            document = service.documents().create(body={
                'title': title
            }).execute()
            
            document_id = document.get('documentId')
            
            # Add content to the document
            requests_list = []
            
            # Add title
            requests_list.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': f'{title}\n\n'
                }
            })
            
            # Add content
            requests_list.append({
                'insertText': {
                    'location': {'index': len(title) + 3},
                    'text': content
                }
            })
            
            # Execute the batch update
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests_list}
            ).execute()
            
            return {
                'document_id': document_id,
                'url': f'https://docs.google.com/document/d/{document_id}',
                'title': title
            }
            
        except Exception as e:
            return {'error': str(e)}

    def create_form(self, title, description, questions):
        """Create a Google Form with the given parameters"""
        creds = self.get_credentials()
        if not creds:
            return {'error': 'Google credentials not configured'}
        
        try:
            service = build('forms', 'v1', credentials=creds)
            
            # Create form metadata
            form_body = {
                'info': {
                    'title': title,
                    'description': description
                }
            }
            
            # Create the form
            form = service.forms().create(body=form_body).execute()
            form_id = form.get('formId')
            
            # Add questions to the form
            for i, question in enumerate(questions):
                question_body = {
                    'requests': [{
                        'createItem': {
                            'item': {
                                'title': question['title'],
                                'questionItem': {
                                    'question': {
                                        'required': question.get('required', False),
                                        'choiceQuestion': {
                                            'type': 'RADIO',
                                            'options': [{'value': opt} for opt in question.get('options', [])],
                                            'shuffle': False
                                        } if question['type'] in ['RADIO', 'CHECKBOX'] else {
                                            'textInput': {
                                                'type': 'PARAGRAPH' if question['type'] == 'PARAGRAPH' else 'SHORT_ANSWER'
                                            }
                                        }
                                    }
                                }
                            },
                            'location': {
                                'index': i
                            }
                        }
                    }]
                }
                
                service.forms().batchUpdate(formId=form_id, body=question_body).execute()
            
            return {
                'form_id': form_id,
                'url': f'https://docs.google.com/forms/d/{form_id}',
                'title': title
            }
            
        except Exception as e:
            return {'error': str(e)}

    def upload_file_to_drive(self, file_path, file_name, mime_type=None):
        """Upload a file to Google Drive"""
        creds = self.get_credentials()
        if not creds:
            return {'error': 'Google credentials not configured'}
        
        try:
            from googleapiclient.http import MediaFileUpload
            drive_service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {'name': file_name}
            media = MediaFileUpload(file_path, mimetype=mime_type)
            
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            return {
                'file_id': file.get('id'),
                'url': file.get('webViewLink')
            }
            
        except Exception as e:
            return {'error': str(e)}
