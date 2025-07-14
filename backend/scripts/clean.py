"""
Database Cleanup Script for Cape Town Property App
Multiple options for cleaning your MongoDB database before fresh scraping
"""

import requests
import pymongo
from datetime import datetime, timedelta
import argparse
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:8000"
MONGODB_URL = "mongodb://localhost:27018"  # Your custom MongoDB port
DATABASE_NAME = "cape_town_properties"

class DatabaseCleaner:
    def __init__(self, use_api=True):
        self.use_api = use_api
        self.api_url = API_URL
        
        if not use_api:
            # Direct MongoDB connection
            try:
                self.client = pymongo.MongoClient(MONGODB_URL)
                self.db = self.client[DATABASE_NAME]
                logger.info("✅ Connected directly to MongoDB")
            except Exception as e:
                logger.error(f"❌ MongoDB connection failed: {e}")
                sys.exit(1)
    
    def cleanup_via_api(self, area=None, older_than_days=None):
        """Clean using your backend API endpoint"""
        try:
            params = {}
            if area:
                params['area'] = area
            if older_than_days:
                params['older_than_days'] = older_than_days
            
            response = requests.delete(
                f"{self.api_url}/api/properties/cleanup",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ {result['message']}")
                logger.info(f"   Deleted: {result['deleted']} properties")
                return True
            else:
                logger.error(f"❌ API cleanup failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API cleanup error: {e}")
            return False
    
    def cleanup_direct_mongodb(self, query=None):
        """Clean directly via MongoDB (when API is down)"""
        if self.use_api:
            logger.error("Direct MongoDB cleanup requires use_api=False")
            return False
        
        try:
            # Clean properties
            if query is None:
                query = {}  # Delete all
            
            result = self.db.properties.delete_many(query)
            logger.info(f"✅ Deleted {result.deleted_count} properties")
            
            # Also clean related data
            if not query:  # If deleting all properties
                comments_result = self.db.comments.delete_many({})
                logger.info(f"✅ Deleted {comments_result.deleted_count} comments")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB cleanup error: {e}")
            return False
    
    def get_stats(self):
        """Get current database statistics"""
        if self.use_api:
            try:
                response = requests.get(f"{self.api_url}/api/scraper/stats")
                if response.status_code == 200:
                    return response.json()
            except:
                pass
        else:
            # Direct MongoDB stats
            try:
                stats = {
                    'total_properties': self.db.properties.count_documents({}),
                    'total_comments': self.db.comments.count_documents({}),
                    'properties_by_area': {}
                }
                
                # Count by area
                pipeline = [
                    {"$group": {"_id": "$area", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                
                for doc in self.db.properties.aggregate(pipeline):
                    stats['properties_by_area'][doc['_id']] = doc['count']
                
                return stats
            except:
                return None
    
    def backup_before_cleanup(self, collection_name='properties'):
        """Create a backup collection before cleanup"""
        if self.use_api:
            logger.warning("⚠️  Backup only available with direct MongoDB connection")
            return None
        
        try:
            backup_name = f"{collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Copy collection
            pipeline = [{"$out": backup_name}]
            self.db[collection_name].aggregate(pipeline)
            
            count = self.db[backup_name].count_documents({})
            logger.info(f"📦 Backup created: {backup_name} ({count} documents)")
            return backup_name
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    def restore_from_backup(self, backup_name, collection_name='properties'):
        """Restore from a backup collection"""
        if self.use_api:
            logger.warning("⚠️  Restore only available with direct MongoDB connection")
            return False
        
        try:
            # Drop current collection
            self.db[collection_name].drop()
            
            # Restore from backup
            pipeline = [{"$out": collection_name}]
            self.db[backup_name].aggregate(pipeline)
            
            count = self.db[collection_name].count_documents({})
            logger.info(f"✅ Restored {count} documents from {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return False
    
    def list_backups(self):
        """List available backup collections"""
        if self.use_api:
            logger.warning("⚠️  Backup listing only available with direct MongoDB connection")
            return []
        
        try:
            collections = self.db.list_collection_names()
            backups = [c for c in collections if c.startswith('properties_backup_')]
            
            if backups:
                logger.info("📦 Available backups:")
                for backup in sorted(backups):
                    count = self.db[backup].count_documents({})
                    logger.info(f"   - {backup} ({count} documents)")
            else:
                logger.info("📦 No backups found")
            
            return backups
            
        except Exception as e:
            logger.error(f"❌ Error listing backups: {e}")
            return []

def main():
    parser = argparse.ArgumentParser(
        description="Clean Cape Town Property Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_database.py --all                    # Delete ALL properties (with confirmation)
  python cleanup_database.py --all --force           # Delete ALL without confirmation
  python cleanup_database.py --area sea-point        # Delete only Sea Point properties
  python cleanup_database.py --older-than 30         # Delete properties older than 30 days
  python cleanup_database.py --stats                 # Show database statistics
  python cleanup_database.py --backup --all          # Backup then delete all
  python cleanup_database.py --direct --all          # Use direct MongoDB (if API is down)
  python cleanup_database.py --list-backups          # Show available backups
        """
    )
    
    # Cleanup options
    parser.add_argument('--all', action='store_true', 
                       help='Delete ALL properties (requires confirmation)')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts')
    parser.add_argument('--area', type=str,
                       help='Delete properties from specific area only')
    parser.add_argument('--older-than', type=int, metavar='DAYS',
                       help='Delete properties older than N days')
    
    # Other options
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics before cleanup')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup before cleanup (direct mode only)')
    parser.add_argument('--restore', type=str, metavar='BACKUP_NAME',
                       help='Restore from specific backup')
    parser.add_argument('--list-backups', action='store_true',
                       help='List available backups')
    parser.add_argument('--direct', action='store_true',
                       help='Use direct MongoDB connection instead of API')
    
    args = parser.parse_args()
    
    # Initialize cleaner
    cleaner = DatabaseCleaner(use_api=not args.direct)
    
    # Handle backup operations
    if args.list_backups:
        cleaner.list_backups()
        return
    
    if args.restore:
        if cleaner.restore_from_backup(args.restore):
            logger.info("✅ Restore completed!")
        return
    
    # Show current stats
    if args.stats or not any([args.all, args.area, args.older_than]):
        stats = cleaner.get_stats()
        if stats:
            logger.info("\n📊 Current Database Statistics:")
            logger.info(f"   Total properties: {stats.get('total_properties', 0)}")
            
            if stats.get('properties_by_area'):
                logger.info("\n📍 Properties by area:")
                for area, count in stats['properties_by_area'].items():
                    logger.info(f"   - {area}: {count}")
        
        if not any([args.all, args.area, args.older_than]):
            logger.info("\n💡 Use --all, --area, or --older-than to clean data")
            return
    
    # Determine what to clean
    if args.all:
        if not args.force:
            logger.warning("\n⚠️  WARNING: This will DELETE ALL properties and comments!")
            confirm = input("Are you SURE? Type 'DELETE ALL' to confirm: ")
            if confirm != 'DELETE ALL':
                logger.info("❌ Cleanup cancelled")
                return
        
        cleanup_desc = "ALL DATA"
        
    elif args.area:
        cleanup_desc = f"properties from {args.area}"
        
    elif args.older_than:
        cleanup_desc = f"properties older than {args.older_than} days"
        
    else:
        logger.error("❌ No cleanup action specified")
        return
    
    # Create backup if requested
    backup_name = None
    if args.backup and not cleaner.use_api:
        logger.info("\n📦 Creating backup before cleanup...")
        backup_name = cleaner.backup_before_cleanup()
    
    # Perform cleanup
    logger.info(f"\n🧹 Cleaning {cleanup_desc}...")
    
    if cleaner.use_api:
        # Use API endpoint
        success = cleaner.cleanup_via_api(
            area=args.area,
            older_than_days=args.older_than
        )
    else:
        # Direct MongoDB cleanup
        query = {}
        if args.area:
            query['area'] = args.area
        if args.older_than:
            cutoff = datetime.now() - timedelta(days=args.older_than)
            query['scraped_at'] = {'$lt': cutoff}
        
        success = cleaner.cleanup_direct_mongodb(query)
    
    if success:
        logger.info("\n✅ Cleanup completed successfully!")
        
        if backup_name:
            logger.info(f"💡 To restore from backup, run:")
            logger.info(f"   python cleanup_database.py --direct --restore {backup_name}")
        
        # Show final stats
        final_stats = cleaner.get_stats()
        if final_stats:
            logger.info(f"\n📊 Remaining properties: {final_stats.get('total_properties', 0)}")
    else:
        logger.error("\n❌ Cleanup failed!")
        
        if cleaner.use_api:
            logger.info("💡 Try using --direct flag to connect directly to MongoDB")

if __name__ == "__main__":
    main()