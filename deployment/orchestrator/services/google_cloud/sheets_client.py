"""
Google Sheets Client for Helios Autonomous Store
Handles tracking, analytics, and reporting via Google Sheets API
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from loguru import logger

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:
    """Google Sheets client for tracking and analytics"""
    
    def __init__(self, service_account_json: str, spreadsheet_id: str):
        """Initialize Google Sheets client
        
        Args:
            service_account_json: Path to service account JSON file or JSON string
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials = self._get_credentials(service_account_json)
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.gspread_client = gspread.authorize(self.credentials)
        
        # Cache for spreadsheet metadata
        self._spreadsheet_cache = {}
        self._last_cache_update = None
        self._cache_ttl = 300  # 5 minutes
    
    def _get_credentials(self, service_account_json: str) -> Credentials:
        """Get Google credentials from service account"""
        try:
            if service_account_json.startswith('~'):
                import os
                service_account_json = os.path.expanduser(service_account_json)
            
            if service_account_json.endswith('.json'):
                # File path
                return Credentials.from_service_account_file(service_account_json)
            else:
                # JSON string
                import json
                service_account_info = json.loads(service_account_json)
                return Credentials.from_service_account_info(service_account_info)
        except Exception as e:
            logger.error(f"Failed to load service account credentials: {e}")
            raise
    
    async def get_spreadsheet_info(self) -> Dict[str, Any]:
        """Get spreadsheet metadata and sheet information"""
        try:
            # Check cache first
            if (self._last_cache_update and 
                (datetime.now(timezone.utc) - self._last_cache_update).seconds < self._cache_ttl):
                return self._spreadsheet_cache
            
            request = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id)
            response = request.execute()
            
            info = {
                'title': response.get('properties', {}).get('title', ''),
                'sheets': [],
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            for sheet in response.get('sheets', []):
                sheet_info = {
                    'id': sheet['properties']['sheetId'],
                    'title': sheet['properties']['title'],
                    'index': sheet['properties']['index'],
                    'row_count': sheet['properties']['gridProperties']['rowCount'],
                    'column_count': sheet['properties']['gridProperties']['columnCount']
                }
                info['sheets'].append(sheet_info)
            
            # Update cache
            self._spreadsheet_cache = info
            self._last_cache_update = datetime.now(timezone.utc)
            
            return info
            
        except HttpError as e:
            logger.error(f"Failed to get spreadsheet info: {e}")
            raise
    
    async def read_sheet(self, sheet_name: str, range_name: Optional[str] = None) -> List[List[Any]]:
        """Read data from a specific sheet
        
        Args:
            sheet_name: Name of the sheet to read
            range_name: Optional range (e.g., 'A1:D10')
        
        Returns:
            List of rows, each row is a list of values
        """
        try:
            if range_name:
                range_spec = f"{sheet_name}!{range_name}"
            else:
                range_spec = sheet_name
            
            request = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_spec
            )
            response = request.execute()
            
            return response.get('values', [])
            
        except HttpError as e:
            logger.error(f"Failed to read sheet {sheet_name}: {e}")
            raise
    
    async def write_sheet(self, sheet_name: str, data: List[List[Any]], 
                         start_cell: str = 'A1') -> Dict[str, Any]:
        """Write data to a specific sheet
        
        Args:
            sheet_name: Name of the sheet to write to
            range_name: Starting cell (e.g., 'A1')
            data: 2D array of data to write
        
        Returns:
            Response from Google Sheets API
        """
        try:
            range_spec = f"{sheet_name}!{start_cell}"
            
            body = {
                'values': data
            }
            
            request = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_spec,
                valueInputOption='RAW',
                body=body
            )
            response = request.execute()
            
            logger.info(f"Updated {response.get('updatedCells', 0)} cells in {sheet_name}")
            return response
            
        except HttpError as e:
            logger.error(f"Failed to write to sheet {sheet_name}: {e}")
            raise
    
    async def append_to_sheet(self, sheet_name: str, data: List[List[Any]]) -> Dict[str, Any]:
        """Append data to the end of a sheet
        
        Args:
            sheet_name: Name of the sheet to append to
            data: 2D array of data to append
        
        Returns:
            Response from Google Sheets API
        """
        try:
            body = {
                'values': data
            }
            
            request = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            )
            response = request.execute()
            
            logger.info(f"Appended {len(data)} rows to {sheet_name}")
            return response
            
        except HttpError as e:
            logger.error(f"Failed to append to sheet {sheet_name}: {e}")
            raise
    
    async def clear_sheet(self, sheet_name: str, range_name: Optional[str] = None) -> Dict[str, Any]:
        """Clear data from a sheet
        
        Args:
            sheet_name: Name of the sheet to clear
            range_name: Optional range to clear (e.g., 'A1:D10')
        
        Returns:
            Response from Google Sheets API
        """
        try:
            if range_name:
                range_spec = f"{sheet_name}!{range_name}"
            else:
                range_spec = sheet_name
            
            request = self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_spec
            )
            response = request.execute()
            
            logger.info(f"Cleared range {range_spec}")
            return response
            
        except HttpError as e:
            logger.error(f"Failed to clear sheet {sheet_name}: {e}")
            raise
    
    async def batch_update(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute multiple operations in a single batch request
        
        Args:
            requests: List of request objects for different operations
        
        Returns:
            Response from Google Sheets API
        """
        try:
            body = {
                'requests': requests
            }
            
            request = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            )
            response = request.execute()
            
            logger.info(f"Executed {len(requests)} batch operations")
            return response
            
        except HttpError as e:
            logger.error(f"Failed to execute batch update: {e}")
            raise
    
    async def create_sheet(self, sheet_name: str) -> Dict[str, Any]:
        """Create a new sheet in the spreadsheet
        
        Args:
            sheet_name: Name of the new sheet
        
        Returns:
            Response from Google Sheets API
        """
        try:
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            response = await self.batch_update([request])
            logger.info(f"Created new sheet: {sheet_name}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create sheet {sheet_name}: {e}")
            raise
    
    async def delete_sheet(self, sheet_id: int) -> Dict[str, Any]:
        """Delete a sheet from the spreadsheet
        
        Args:
            sheet_id: ID of the sheet to delete
        
        Returns:
            Response from Google Sheets API
        """
        try:
            request = {
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }
            
            response = await self.batch_update([request])
            logger.info(f"Deleted sheet with ID: {sheet_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to delete sheet {sheet_id}: {e}")
            raise
    
    # Helios-specific methods for tracking and analytics
    
    async def log_trend_discovery(self, trend_data: Dict[str, Any]) -> bool:
        """Log a new trend discovery to the tracking sheet
        
        Args:
            trend_data: Dictionary containing trend information
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            row_data = [
                timestamp,
                trend_data.get('trend_name', ''),
                trend_data.get('opportunity_score', 0),
                trend_data.get('keywords', []),
                trend_data.get('source', ''),
                trend_data.get('volume', 0),
                trend_data.get('growth_rate', 0),
                trend_data.get('competition_level', ''),
                json.dumps(trend_data.get('metadata', {}))
            ]
            
            await self.append_to_sheet('Trend_Analysis', [row_data])
            logger.info(f"Logged trend discovery: {trend_data.get('trend_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log trend discovery: {e}")
            return False
    
    async def log_product_launch(self, product_data: Dict[str, Any]) -> bool:
        """Log a product launch to the tracking sheet
        
        Args:
            product_data: Dictionary containing product information
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            row_data = [
                timestamp,
                product_data.get('product_name', ''),
                product_data.get('trend_name', ''),
                product_data.get('printify_product_id', ''),
                product_data.get('etsy_listing_id', ''),
                product_data.get('status', ''),
                product_data.get('profit_margin', 0),
                product_data.get('design_count', 0),
                json.dumps(product_data.get('metadata', {}))
            ]
            
            await self.append_to_sheet('Product_Launches', [row_data])
            logger.info(f"Logged product launch: {product_data.get('product_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log product launch: {e}")
            return False
    
    async def log_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Log performance metrics to the tracking sheet
        
        Args:
            metrics: Dictionary containing performance metrics
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            row_data = [
                timestamp,
                metrics.get('pipeline_execution_time', 0),
                metrics.get('trend_score', 0),
                metrics.get('audience_confidence', 0),
                metrics.get('designs_generated', 0),
                metrics.get('products_published', 0),
                metrics.get('success_prediction', 0),
                metrics.get('optimization_triggers', []),
                json.dumps(metrics.get('metadata', {}))
            ]
            
            await self.append_to_sheet('Performance_Dashboard', [row_data])
            logger.info("Logged performance metrics")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log performance metrics: {e}")
            return False
    
    async def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary from the tracking sheet
        
        Returns:
            Dictionary containing financial summary
        """
        try:
            data = await self.read_sheet('Financial_Summary')
            
            if not data or len(data) < 2:
                return {}
            
            # Assume first row is headers
            headers = data[0]
            latest_row = data[-1]
            
            summary = {}
            for i, header in enumerate(headers):
                if i < len(latest_row):
                    summary[header] = latest_row[i]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get financial summary: {e}")
            return {}
    
    async def update_roi_calculations(self) -> bool:
        """Update ROI calculations in the financial summary sheet
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would typically involve complex calculations
            # For now, we'll just log that it was attempted
            logger.info("ROI calculations update requested")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ROI calculations: {e}")
            return False
