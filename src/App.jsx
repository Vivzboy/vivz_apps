import React, { useState, useEffect } from 'react';
import { Heart, MapPin, Bed, Bath, Square, Eye, BarChart3, ExternalLink, Filter, Search, X, MessageCircle, Send, Loader } from 'lucide-react';

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// API Client
class PropertyAPIClient {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Property endpoints
  async getProperties(filters = {}) {
    const queryParams = new URLSearchParams();
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        queryParams.append(key, value);
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/api/properties${queryString ? `?${queryString}` : ''}`;
    
    return this.request(endpoint);
  }

  async getProperty(id) {
    return this.request(`/api/properties/${id}`);
  }

  // Social features
  async trackView(propertyId) {
    return this.request(`/api/properties/${propertyId}/view`, {
      method: 'POST',
    });
  }

  async toggleLike(propertyId) {
    return this.request(`/api/properties/${propertyId}/like`, {
      method: 'POST',
    });
  }

  async getComments(propertyId) {
    return this.request(`/api/properties/${propertyId}/comments`);
  }

  async addComment(propertyId, commentData) {
    return this.request(`/api/properties/${propertyId}/comments`, {
      method: 'POST',
      body: JSON.stringify(commentData),
    });
  }

  async likeComment(commentId) {
    return this.request(`/api/comments/${commentId}/like`, {
      method: 'POST',
    });
  }

  // Analytics
  async getMarketAnalytics(area = null) {
    const endpoint = `/api/analytics/market${area ? `?area=${area}` : ''}`;
    return this.request(endpoint);
  }

  async getAreas() {
    return this.request('/api/areas');
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }
}

// Create API client instance
const apiClient = new PropertyAPIClient();

// Property status constants
const PROPERTY_STATUS = {
  AVAILABLE: 'available',
  UNDER_OFFER: 'under_offer',
  SOLD: 'sold',
  OFF_MARKET: 'off_market'
};

// Filter configurations
const LIFESTYLE_FILTERS = [
  { id: 'beach_walk', label: '🏖️ Beach Walking', areas: ['sea-point', 'camps-bay', 'clifton'], active: false },
  { id: 'coffee_scene', label: '☕ Great Coffee', areas: ['sea-point', 'green-point', 'de-waterkant'], active: false },
  { id: 'family_friendly', label: '👨‍👩‍👧 Family Area', areas: ['gardens', 'oranjezicht', 'vredehoek'], active: false },
  { id: 'nightlife', label: '🌃 Vibrant Scene', areas: ['green-point', 'de-waterkant', 'sea-point'], active: false },
  { id: 'mountain_views', label: '⛰️ Mountain Views', areas: ['gardens', 'oranjezicht', 'tamboerskloof'], active: false },
  { id: 'pet_friendly', label: '🐕 Pet Paradise', areas: ['sea-point', 'green-point', 'gardens'], active: false }
];

const BUDGET_FILTERS = [
  { id: 'starter', label: '🌱 Starter Homes', value: { max_price: 1500000 }, active: false },
  { id: 'upgrade', label: '📈 Upgrade Ready', value: { min_price: 1500000, max_price: 3000000 }, active: false },
  { id: 'investment', label: '💎 Investment Grade', value: { min_price: 2000000, max_price: 5000000 }, active: false },
  { id: 'luxury', label: '🏰 Dream Homes', value: { min_price: 5000000 }, active: false }
];

const PROPERTY_TYPE_FILTERS = [
  { id: 'apartment', label: '🏢 Apartments', type: 'Apartment', active: false },
  { id: 'house', label: '🏡 Houses', type: 'House', active: false },
  { id: 'penthouse', label: '🌆 Penthouses', search: 'penthouse', active: false },
  { id: 'character', label: '🏛️ Character Homes', search: 'character victorian', active: false }
];

// Property Card Component with Backend Integration
const PropertyCard = ({ property, onToggleFavorite, isFavorited, onAddToCompare, isComparing }) => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [isImageExpanded, setIsImageExpanded] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [loadingComments, setLoadingComments] = useState(false);
  const [hasViewed, setHasViewed] = useState(false);
  const [localViews, setLocalViews] = useState(property.views || 0);
  const [localLikes, setLocalLikes] = useState(property.likes || 0);

  // Track view when component mounts
  useEffect(() => {
    if (!hasViewed && property.id) {
      trackView();
      setHasViewed(true);
    }
  }, [property.id, hasViewed]);

  // Load comments when comment section is opened
  useEffect(() => {
    if (showComments && property.id) {
      loadComments();
    }
  }, [showComments, property.id]);

  const trackView = async () => {
    try {
      const result = await apiClient.trackView(property.id);
      setLocalViews(result.total_views);
    } catch (error) {
      console.error('Failed to track view:', error);
    }
  };

  const handleToggleLike = async () => {
    try {
      const result = await apiClient.toggleLike(property.id);
      setLocalLikes(result.total_likes);
      onToggleFavorite(property.id);
    } catch (error) {
      console.error('Failed to toggle like:', error);
      // Still update UI optimistically
      onToggleFavorite(property.id);
    }
  };

  const loadComments = async () => {
    setLoadingComments(true);
    try {
      const commentsData = await apiClient.getComments(property.id);
      setComments(commentsData);
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;

    try {
      const commentData = {
        user_name: "You", // In real app, get from user session
        user_avatar: "👤",
        text: newComment.trim()
      };

      const newCommentObj = await apiClient.addComment(property.id, commentData);
      setComments(prev => [newCommentObj, ...prev]);
      setNewComment('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const handleLikeComment = async (commentId) => {
    try {
      const result = await apiClient.likeComment(commentId);
      setComments(prev =>
        prev.map(comment =>
          comment.id === commentId
            ? { ...comment, likes: result.total_likes }
            : comment
        )
      );
    } catch (error) {
      console.error('Failed to like comment:', error);
    }
  };

  // Image navigation
  const nextImage = () => {
    setCurrentImageIndex((prev) => 
      prev === property.images.length - 1 ? 0 : prev + 1
    );
  };

  const prevImage = () => {
    setCurrentImageIndex((prev) => 
      prev === 0 ? property.images.length - 1 : prev - 1
    );
  };

  // Utility functions
  const formatPrice = (price) => {
    if (!price) return "POA";
    if (price >= 1000000) {
      return `R${(price / 1000000).toFixed(1)}M`;
    }
    return `R${(price / 1000).toFixed(0)}k`;
  };

  const formatNumber = (num) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`;
    }
    return num.toString();
  };

  const getStatusInfo = (status) => {
    switch (status) {
      case PROPERTY_STATUS.AVAILABLE:
        return {
          badge: '🟢 Available',
          badgeColor: 'bg-green-500',
          overlay: null,
          actionable: true
        };
      case PROPERTY_STATUS.UNDER_OFFER:
        return {
          badge: '🟡 Under Offer',
          badgeColor: 'bg-yellow-500',
          overlay: 'bg-yellow-500/20',
          actionable: false
        };
      case PROPERTY_STATUS.SOLD:
        return {
          badge: '🔴 SOLD',
          badgeColor: 'bg-red-500',
          overlay: 'bg-red-500/30',
          actionable: false
        };
      case PROPERTY_STATUS.OFF_MARKET:
        return {
          badge: '⚫ Off Market',
          badgeColor: 'bg-gray-600',
          overlay: 'bg-gray-500/40',
          actionable: false
        };
      default:
        return {
          badge: '🟢 Available',
          badgeColor: 'bg-green-500',
          overlay: null,
          actionable: true
        };
    }
  };

  const statusInfo = getStatusInfo(property.status);

  // Get display image (use real images if available, fallback to gradients)
  const getDisplayImage = (index) => {
    if (property.images && property.images[index]) {
      return property.images[index];
    }
    
    // Fallback gradients for properties without images
    const gradients = [
      "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
      "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
      "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
    ];
    
    return gradients[index % gradients.length];
  };

  const imageLabels = ["Main Photo", "Interior", "Exterior", "Additional"];
  const displayImages = property.images || [null, null, null, null];

  return (
    <div className={`bg-white rounded-2xl shadow-lg overflow-hidden mb-6 max-w-md mx-auto ${!statusInfo.actionable ? 'opacity-90' : ''}`}>
      {/* Image Gallery Section */}
      <div className="relative h-64 bg-gray-200">
        {property.images && property.images.length > 0 && property.images[currentImageIndex] ? (
          <img
            src={property.images[currentImageIndex]}
            alt={property.title}
            className="w-full h-full object-cover cursor-pointer"
            onClick={() => setIsImageExpanded(true)}
            onError={(e) => {
              console.log('Image failed to load:', e.target.src);
              // Hide the broken image
              e.target.style.display = 'none';
              // Show the fallback div
              if (e.target.nextElementSibling) {
                e.target.nextElementSibling.style.display = 'flex';
              }
            }}
          />
        ) : (
          <div 
            className="w-full h-full flex items-center justify-center text-white text-xl font-bold cursor-pointer"
            style={{
              background: property.images && property.images.length > 0 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : (() => {
                    const gradients = [
                      "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                      "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
                      "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
                      "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
                    ];
                    return gradients[currentImageIndex % gradients.length];
                  })()
            }}
            onClick={() => setIsImageExpanded(true)}
          >
            No Image Available
          </div>
        )}
        
        {/* Fallback div for when image fails to load */}
        <div 
          className="w-full h-full flex items-center justify-center text-white text-xl font-bold cursor-pointer"
          style={{
            display: 'none',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
          }}
          onClick={() => setIsImageExpanded(true)}
        >
          Image Failed to Load
        </div>
        
        {/* Status overlay */}
        {statusInfo.overlay && (
          <div className={`absolute inset-0 ${statusInfo.overlay} flex items-center justify-center`}>
            <div className="bg-white/90 backdrop-blur-sm px-6 py-3 rounded-lg text-center">
              <div className="text-lg font-bold text-gray-900">{statusInfo.badge}</div>
            </div>
          </div>
        )}
        
        {/* Image navigation */}
        {displayImages.length > 1 && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2">
            {displayImages.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentImageIndex(idx)}
                className={`w-2 h-2 rounded-full transition-all ${
                  idx === currentImageIndex ? 'bg-white' : 'bg-white/50'
                }`}
              />
            ))}
          </div>
        )}
        
        {/* Status badge */}
        <div className={`absolute top-4 left-4 ${statusInfo.badgeColor} text-white px-3 py-1 rounded-full text-sm font-medium`}>
          {statusInfo.badge}
        </div>
        
        {/* Deal badge */}
        {property.deal && statusInfo.actionable && (
          <div className="absolute top-4 left-32 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
            💚 Deal Alert
          </div>
        )}
        
        {/* Engagement stats */}
        <div className="absolute top-4 right-4 flex flex-col space-y-1">
          <div className="bg-black/20 backdrop-blur-sm text-white px-3 py-1 rounded-full text-sm flex items-center">
            <Eye className="w-3 h-3 mr-1" />
            {formatNumber(localViews)}
          </div>
          <div className="bg-black/20 backdrop-blur-sm text-white px-3 py-1 rounded-full text-sm flex items-center">
            <Heart className="w-3 h-3 mr-1" />
            {formatNumber(localLikes)}
          </div>
        </div>
      </div>

      {/* Property Details */}
      <div className="p-5">
        {/* Title and Location */}
        <div className="mb-3">
          <h3 className="text-xl font-bold text-gray-900 mb-1">{property.title}</h3>
          <div className="flex items-center text-gray-600">
            <MapPin className="w-4 h-4 mr-1" />
            <span className="text-sm">
              {property.highlights ? property.highlights.join(' • ') : property.area}
            </span>
          </div>
        </div>

        {/* Key Stats */}
        <div className="flex items-center justify-between mb-4">
          <div className="text-2xl font-bold text-gray-900">
            {formatPrice(property.price)}
          </div>
          <div className="flex items-center space-x-4 text-gray-600">
            <div className="flex items-center">
              <Bed className="w-4 h-4 mr-1" />
              <span className="text-sm">{property.bedrooms || '?'}</span>
            </div>
            <div className="flex items-center">
              <Bath className="w-4 h-4 mr-1" />
              <span className="text-sm">{property.bathrooms || '?'}</span>
            </div>
            <div className="flex items-center">
              <Square className="w-4 h-4 mr-1" />
              <span className="text-sm">{property.size_sqm || '?'}m²</span>
            </div>
          </div>
        </div>

        {/* Price per sqm */}
        {property.price_per_sqm && (
          <div className="text-sm text-gray-500 mb-4">
            R{Math.round(property.price_per_sqm).toLocaleString()}/m² • {property.neighborhood_vibe || property.area}
          </div>
        )}

        {/* Engagement Bar */}
        <div className="flex items-center justify-between mb-4 text-sm text-gray-500">
          <button 
            onClick={() => setShowComments(!showComments)}
            className="flex items-center hover:text-gray-700 transition-colors"
          >
            <MessageCircle className="w-4 h-4 mr-1" />
            {comments.length} comments
          </button>
          <div className="flex items-center space-x-4">
            <span className="flex items-center">
              <Eye className="w-4 h-4 mr-1" />
              {formatNumber(localViews)} views
            </span>
            <span className="flex items-center">
              <Heart className="w-4 h-4 mr-1" />
              {formatNumber(localLikes)} likes
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3 mb-4">
          <button
            onClick={handleToggleLike}
            className={`flex-1 flex items-center justify-center px-4 py-2 rounded-xl font-medium transition-all ${
              isFavorited 
                ? 'bg-red-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Heart className={`w-4 h-4 mr-2 ${isFavorited ? 'fill-current' : ''}`} />
            {isFavorited ? 'Saved' : 'Save'}
          </button>
          
          <button
            onClick={() => onAddToCompare(property)}
            disabled={isComparing}
            className="flex-1 flex items-center justify-center px-4 py-2 bg-blue-100 text-blue-700 rounded-xl font-medium hover:bg-blue-200 disabled:opacity-50"
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Compare
          </button>
          
          {property.url && statusInfo.actionable ? (
            <a 
              href={property.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center px-4 py-2 bg-green-100 text-green-700 rounded-xl font-medium hover:bg-green-200"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View
            </a>
          ) : (
            <button 
              disabled
              className="flex-1 flex items-center justify-center px-4 py-2 bg-gray-100 text-gray-500 rounded-xl font-medium cursor-not-allowed"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              {statusInfo.badge.replace(/🔴|🟡|⚫|🟢/, '').trim()}
            </button>
          )}
        </div>

        {/* Comments Section */}
        {showComments && (
          <div className="border-t pt-4">
            {loadingComments ? (
              <div className="flex items-center justify-center py-4">
                <Loader className="w-6 h-6 animate-spin text-gray-400" />
                <span className="ml-2 text-gray-500">Loading comments...</span>
              </div>
            ) : (
              <>
                {/* Existing Comments */}
                <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
                  {comments.map(comment => (
                    <div key={comment.id} className="flex space-x-3">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-sm">
                          {comment.user_avatar}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-sm font-medium text-gray-900">
                            {comment.user_name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(comment.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 mb-2">{comment.text}</p>
                        <div className="flex items-center space-x-4">
                          <button 
                            onClick={() => handleLikeComment(comment.id)}
                            className="text-xs text-gray-500 hover:text-red-500 transition-colors flex items-center"
                          >
                            <Heart className="w-3 h-3 mr-1" />
                            {comment.likes}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Add Comment */}
                <div className="flex space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm text-white">
                      You
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        placeholder="Add a comment..."
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                        className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        onClick={handleAddComment}
                        disabled={!newComment.trim()}
                        className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Filter Chip Component
const FilterChip = ({ filter, onToggle }) => (
  <button
    onClick={() => onToggle(filter.id)}
    className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
      filter.active 
        ? 'bg-blue-500 text-white' 
        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
    }`}
  >
    {filter.label}
  </button>
);

// Main App Component with Backend Integration
const PropertyDiscoveryApp = () => {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [favorites, setFavorites] = useState(new Set());
  const [compareList, setCompareList] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [lifestyleFilters, setLifestyleFilters] = useState(LIFESTYLE_FILTERS);
  const [budgetFilters, setBudgetFilters] = useState(BUDGET_FILTERS);
  const [propertyTypeFilters, setPropertyTypeFilters] = useState(PROPERTY_TYPE_FILTERS);
  const [searchQuery, setSearchQuery] = useState('');
  const [areas, setAreas] = useState([]);

  // Debug logging
  useEffect(() => {
    console.log('ShowFilters state:', showFilters);
    console.log('Lifestyle filters:', lifestyleFilters);
  }, [showFilters, lifestyleFilters]);

  // Load initial data
  useEffect(() => {
    loadProperties();
    loadAreas();
  }, []);

  // Reload properties when filters change
  useEffect(() => {
    loadProperties();
  }, [lifestyleFilters, budgetFilters, propertyTypeFilters, searchQuery]);

  const loadProperties = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Build filters
      const filters = {};
      
      if (searchQuery) {
        filters.search = searchQuery;
      }
      
      // Lifestyle filters (filter by areas)
      const activeLifestyleFilters = lifestyleFilters.filter(f => f.active);
      if (activeLifestyleFilters.length > 0) {
        // Get all areas that match active lifestyle filters
        const lifestyleAreas = new Set();
        activeLifestyleFilters.forEach(filter => {
          filter.areas.forEach(area => lifestyleAreas.add(area));
        });
        
        // For now, we'll load all and filter client-side
        // In a real app, we'd want the backend to support multiple area filtering
        filters._lifestyle_areas = Array.from(lifestyleAreas);
      }
      
      // Property type filters
      const activeTypeFilters = propertyTypeFilters.filter(f => f.active);
      if (activeTypeFilters.length > 0) {
        if (activeTypeFilters.length === 1) {
          const typeFilter = activeTypeFilters[0];
          if (typeFilter.type) {
            filters.property_type = typeFilter.type;
          } else if (typeFilter.search) {
            filters.search = (filters.search ? filters.search + ' ' : '') + typeFilter.search;
          }
        }
        // If multiple type filters, we'd need to handle this differently
      }
      
      // Budget filters
      const activeBudgetFilters = budgetFilters.filter(f => f.active);
      if (activeBudgetFilters.length > 0) {
        const budgetFilter = activeBudgetFilters[0];
        if (budgetFilter.value.min_price) filters.min_price = budgetFilter.value.min_price;
        if (budgetFilter.value.max_price) filters.max_price = budgetFilter.value.max_price;
      }
      
      // Get all properties first
      const data = await apiClient.getProperties(filters);
      
      // Client-side filtering for lifestyle areas (temporary solution)
      let filteredData = data;
      if (filters._lifestyle_areas && filters._lifestyle_areas.length > 0) {
        filteredData = data.filter(property => {
          const normalizedArea = property.area.toLowerCase().replace(' ', '-');
          return filters._lifestyle_areas.includes(normalizedArea);
        });
      }
      
      setProperties(filteredData);
    } catch (err) {
      setError(`Failed to load properties: ${err.message}`);
      console.error('Error loading properties:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAreas = async () => {
    try {
      const areasData = await apiClient.getAreas();
      setAreas(areasData);
    } catch (err) {
      console.error('Error loading areas:', err);
    }
  };

  const toggleFavorite = (propertyId) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(propertyId)) {
        newFavorites.delete(propertyId);
      } else {
        newFavorites.add(propertyId);
      }
      return newFavorites;
    });
  };

  const addToCompare = (property) => {
    if (compareList.length < 3 && !compareList.find(p => p.id === property.id)) {
      setCompareList(prev => [...prev, property]);
    }
  };

  const removeFromCompare = (propertyId) => {
    setCompareList(prev => prev.filter(p => p.id !== propertyId));
  };

  const toggleLifestyleFilter = (filterId) => {
    setLifestyleFilters(prev => 
      prev.map(filter => ({
        ...filter,
        active: filter.id === filterId ? !filter.active : filter.active
      }))
    );
  };

  const togglePropertyTypeFilter = (filterId) => {
    setPropertyTypeFilters(prev => 
      prev.map(filter => ({
        ...filter,
        active: filter.id === filterId ? !filter.active : false // Only one type at a time
      }))
    );
  };

  const toggleBudgetFilter = (filterId) => {
    setBudgetFilters(prev => 
      prev.map(filter => ({
        ...filter,
        active: filter.id === filterId ? !filter.active : false // Only one budget at a time
      }))
    );
  };

  if (loading && properties.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading properties...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 mb-4">⚠️ Connection Error</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={loadProperties}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Property Feed</h1>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="p-2 bg-gray-100 rounded-full hover:bg-gray-200"
              >
                <Filter className="w-5 h-5" />
              </button>
              {favorites.size > 0 && (
                <div className="relative">
                  <Heart className="w-6 h-6 text-red-500 fill-current" />
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {favorites.size}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search properties, areas, or features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-gray-100 rounded-xl border-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
            />
            {loading && (
              <Loader className="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 animate-spin text-gray-400" />
            )}
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="border-t bg-white px-4 py-4">
            <div className="max-w-md mx-auto">
              <h3 className="font-medium text-gray-900 mb-3">Lifestyle</h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {lifestyleFilters.map(filter => (
                  <FilterChip 
                    key={filter.id} 
                    filter={filter} 
                    onToggle={toggleLifestyleFilter} 
                  />
                ))}
              </div>
              
              <h3 className="font-medium text-gray-900 mb-3">Property Type</h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {propertyTypeFilters.map(filter => (
                  <FilterChip 
                    key={filter.id} 
                    filter={filter} 
                    onToggle={togglePropertyTypeFilter} 
                  />
                ))}
              </div>
              
              <h3 className="font-medium text-gray-900 mb-3">Budget</h3>
              <div className="flex flex-wrap gap-2">
                {budgetFilters.map(filter => (
                  <FilterChip 
                    key={filter.id} 
                    filter={filter} 
                    onToggle={toggleBudgetFilter} 
                  />
                ))}
              </div>
              
              {/* Show active filter summary */}
              {(lifestyleFilters.some(f => f.active) || 
                budgetFilters.some(f => f.active) || 
                propertyTypeFilters.some(f => f.active)) && (
                <div className="mt-4 pt-4 border-t">
                  <button
                    onClick={() => {
                      setLifestyleFilters(LIFESTYLE_FILTERS);
                      setBudgetFilters(BUDGET_FILTERS);
                      setPropertyTypeFilters(PROPERTY_TYPE_FILTERS);
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Comparison Bar */}
      {compareList.length > 0 && (
        <div className="bg-blue-50 border-b px-4 py-3">
          <div className="max-w-md mx-auto">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-blue-800">
                Comparing {compareList.length} properties
              </span>
              <div className="flex items-center space-x-2">
                {compareList.map(property => (
                  <div key={property.id} className="flex items-center bg-white rounded-lg px-2 py-1">
                    <span className="text-xs text-gray-600 mr-1">{property.area}</span>
                    <button
                      onClick={() => removeFromCompare(property.id)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Property Feed */}
      <div className="px-4 py-6">
        <div className="max-w-md mx-auto">
          {properties.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <Search className="w-12 h-12 mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No properties found</h3>
              <p className="text-gray-500">Try adjusting your filters or search terms</p>
            </div>
          ) : (
            properties.map(property => (
              <PropertyCard
                key={property.id}
                property={property}
                onToggleFavorite={toggleFavorite}
                isFavorited={favorites.has(property.id)}
                onAddToCompare={addToCompare}
                isComparing={compareList.length >= 3}
              />
            ))
          )}
        </div>
      </div>

      {/* Bottom stats */}
      <div className="text-center text-gray-500 text-sm pb-8">
        Showing {properties.length} properties
      </div>
    </div>
  );
};

function App() {
  return <PropertyDiscoveryApp />;
}

export default App;
