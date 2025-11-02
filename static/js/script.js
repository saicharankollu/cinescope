document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const resultsDiv = document.getElementById('results');

    // Auto-search if parameter exists
    const urlParams = new URLSearchParams(window.location.search);
    const autoSearch = urlParams.get('search') || sessionStorage.getItem('autoSearch');
    if (autoSearch && searchInput) {
        searchInput.value = autoSearch;
        sessionStorage.removeItem('autoSearch');
        searchMovie(autoSearch);
    }

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            
            if (query) {
                searchMovie(query);
            }
        });
    }

    function searchMovie(query) {
        showLoading();
        
        fetch(`/search?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Search failed');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    displayResults(data);
                }
            })
            .catch(error => {
                // Silently handle errors - user sees friendly message
                showError(error.message || 'Error searching for movie. Please try again.');
            });
    }

    function showLoading() {
        if (!resultsDiv) return;
        resultsDiv.innerHTML = `
            <div class="text-center py-5 loading-container">
                <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted mb-0">Searching OMDB for movies...</p>
            </div>
        `;
    }

    function showError(message) {
        if (!resultsDiv) return;
        resultsDiv.innerHTML = `
            <div class="alert alert-danger shadow-lg">
                <i class="fas fa-exclamation-triangle me-2"></i> ${escapeHtml(message)}
            </div>
        `;
        // Smooth scroll to error
        setTimeout(() => {
            resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }

    // Store current movie data and recommendation state
    let currentMovieData = null;
    let shownRecommendationTitles = [];
    let currentRecommendationPage = 1;
    let hasMoreRecommendations = false;

    function displayResults(data) {
        const movie = data.movie;
        const recommendations = data.recommendations || [];
        const isFavorite = movie.is_favorite || false;
        const movieId = movie.imdb_id || 'N/A';
        
        // Store current movie data for pagination
        currentMovieData = movie;
        shownRecommendationTitles = [movie.title]; // Exclude current movie
        currentRecommendationPage = data.recommendation_page || 1;
        hasMoreRecommendations = data.has_more_recommendations || false;

        let html = `
            <div class="movie-details card mb-5 shadow-lg border-0">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <h2 class="card-title mb-0 fw-bold">
                        <i class="fas fa-film me-2"></i>${movie.title}
                    </h2>
                    ${movieId !== 'N/A' ? `
                    <button class="favorite-btn ${isFavorite ? 'active' : ''}" onclick="toggleFavorite('${movieId}', '${movie.title.replace(/'/g, "\\'")}')">
                        <i class="fas fa-heart"></i> ${isFavorite ? 'Remove from Favorites' : 'Add to Favorites'}
                    </button>
                    ` : ''}
                </div>
                <div class="card-body p-4">
                    <div class="row g-4">
                        <div class="col-md-4 text-center">
                            <div class="poster-img-container">
                                <img src="${movie.poster || 'https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'}" 
                                     alt="${escapeHtml(movie.title)}" 
                                     class="img-fluid poster-img" 
                                     loading="lazy"
                                     onload="this.classList.add('loaded')"
                                     onerror="this.onerror=null; this.src='https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster+Available'; this.classList.add('loaded');">
                            </div>
                        </div>
                        <div class="col-md-8">
                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-star text-warning"></i> Rating:</strong> 
                                        <span class="badge bg-warning text-dark ms-2">${movie.rating}</span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-calendar text-primary"></i> Year:</strong> ${movie.year}
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-clock text-info"></i> Runtime:</strong> ${movie.runtime}
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-globe text-success"></i> Language:</strong> ${movie.language}
                                    </div>
                                </div>
                                <div class="col-md-12">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-tags text-danger"></i> Genre:</strong> 
                                        <span class="badge bg-primary">${movie.genre}</span>
                                    </div>
                                </div>
                                ${movie.box_office !== 'N/A' ? `
                                <div class="col-md-6">
                                    <div class="movie-info-item">
                                        <strong><i class="fas fa-money-bill-wave text-success"></i> Box Office:</strong> ${movie.box_office}
                                    </div>
                                </div>
                                ` : ''}
                            </div>
                            <hr class="my-4">
                            <div class="mb-3">
                                <strong class="d-block mb-2">
                                    <i class="fas fa-user text-primary"></i> Director:
                                </strong>
                                <p class="ms-4 mb-0">${movie.director}</p>
                            </div>
                            <div class="mb-3">
                                <strong class="d-block mb-2">
                                    <i class="fas fa-users text-primary"></i> Cast:
                                </strong>
                                <p class="ms-4 mb-0">${movie.actors}</p>
                            </div>
                            <div class="mt-4">
                                <strong class="d-block mb-2">
                                    <i class="fas fa-align-left text-primary"></i> Plot Summary:
                                </strong>
                                <p class="ms-4 text-muted lh-lg">${movie.summary}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (recommendations && recommendations.length > 0) {
            // Add shown titles to exclusion list
            recommendations.forEach(rec => {
                if (rec.title && !shownRecommendationTitles.includes(rec.title)) {
                    shownRecommendationTitles.push(rec.title);
                }
            });
            
            html += `
                <div class="recommendations mt-5" id="recommendationsSection">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div class="d-flex align-items-center">
                            <h3 class="mb-0 fw-bold">
                                <i class="fas fa-lightbulb text-warning me-2"></i>Personalized Recommendations
                            </h3>
                            <span class="badge bg-primary ms-3">${recommendations.length}</span>
                            <small class="text-muted ms-3">
                                <i class="fas fa-info-circle"></i> Based on genre, director, cast & more
                            </small>
                        </div>
                    </div>
                    <div class="row g-4" id="recommendationsContainer">
            `;
            
            recommendations.forEach(rec => {
                html += `
                    <div class="col-md-4">
                        <div class="card recommendation-card movie-card h-100 shadow border-0">
                            <div class="position-relative">
                                <img src="${rec.poster || 'https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'}" 
                                     class="card-img-top" 
                                     alt="${escapeHtml(rec.title || 'Movie')}"
                                     loading="lazy"
                                     onload="this.classList.add('loaded')"
                                     onerror="this.onerror=null; this.src='https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'; this.classList.add('loaded');">
                                <div class="position-absolute top-0 end-0 p-2">
                                    <span class="badge bg-primary">${rec.year || 'N/A'}</span>
                                </div>
                            </div>
                            <div class="card-body d-flex flex-column">
                                <h5 class="card-title fw-bold">${escapeHtml(rec.title || 'Unknown')}</h5>
                                <p class="card-text text-muted mb-2">
                                    <small><i class="fas fa-tags me-1"></i>${rec.genre || 'N/A'}</small>
                                </p>
                                ${rec.director && rec.director !== 'N/A' ? `
                                <p class="card-text text-muted mb-2">
                                    <small><i class="fas fa-user me-1"></i>${rec.director}</small>
                                </p>
                                ` : ''}
                                <p class="card-text mb-auto">
                                    <i class="fas fa-star text-warning me-1"></i>
                                    <strong>${rec.rating || 'N/A'}</strong>
                                </p>
                                <button class="btn btn-sm btn-outline-primary mt-3" onclick="triggerMovieSearch('${(rec.title || '').replace(/'/g, "\\'")}')">
                                    <i class="fas fa-search me-1"></i>View Details
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                    </div>
                    ${hasMoreRecommendations ? `
                    <div class="text-center mt-4">
                        <button class="btn btn-primary btn-lg" id="loadMoreRecommendationsBtn" onclick="loadMoreRecommendations()">
                            <i class="fas fa-arrow-right me-2"></i>Show More Recommendations
                        </button>
                        <p class="text-muted mt-2 mb-0"><small>Discover more movies similar to "${escapeHtml(movie.title)}"</small></p>
                    </div>
                    ` : ''}
                </div>
            `;
        }

        resultsDiv.innerHTML = html;
        
        // Smooth scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Global function to load more recommendations
    window.loadMoreRecommendations = function() {
        if (!currentMovieData) return;
        
        const btn = document.getElementById('loadMoreRecommendationsBtn');
        const container = document.getElementById('recommendationsContainer');
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        }
        
        fetch('/get_recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                movie_data: currentMovieData,
                page: currentRecommendationPage + 1,
                exclude_titles: shownRecommendationTitles
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // Show error in a more user-friendly way
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
                errorDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(data.error)}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                const container = document.getElementById('recommendationsSection');
                if (container) container.appendChild(errorDiv);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-arrow-right me-2"></i>Show More Recommendations';
                }
                return;
            }
            
            const newRecommendations = data.recommendations || [];
            hasMoreRecommendations = data.has_more_recommendations || false;
            currentRecommendationPage = data.recommendation_page || currentRecommendationPage + 1;
            
            // Add new recommendations to container
            newRecommendations.forEach(rec => {
                if (rec.title && !shownRecommendationTitles.includes(rec.title)) {
                    shownRecommendationTitles.push(rec.title);
                    
                    const recHTML = `
                        <div class="col-md-4">
                            <div class="card recommendation-card movie-card h-100 shadow border-0">
                                <div class="position-relative">
                                    <img src="${rec.poster || 'https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'}" 
                                         class="card-img-top" 
                                         alt="${escapeHtml(rec.title)}"
                                         loading="lazy"
                                         onload="this.classList.add('loaded')"
                                         onerror="this.onerror=null; this.src='https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'; this.classList.add('loaded');">
                                    <div class="position-absolute top-0 end-0 p-2">
                                        <span class="badge bg-primary">${rec.year || 'N/A'}</span>
                                    </div>
                                </div>
                                <div class="card-body d-flex flex-column">
                                    <h5 class="card-title fw-bold">${escapeHtml(rec.title)}</h5>
                                    <p class="card-text text-muted mb-2">
                                        <small><i class="fas fa-tags me-1"></i>${rec.genre || 'N/A'}</small>
                                    </p>
                                    ${rec.director && rec.director !== 'N/A' ? `
                                    <p class="card-text text-muted mb-2">
                                        <small><i class="fas fa-user me-1"></i>${rec.director}</small>
                                    </p>
                                    ` : ''}
                                    <p class="card-text mb-auto">
                                        <i class="fas fa-star text-warning me-1"></i>
                                        <strong>${rec.rating || 'N/A'}</strong>
                                    </p>
                                    <button class="btn btn-sm btn-outline-primary mt-3" onclick="triggerMovieSearch('${rec.title.replace(/'/g, "\\'")}')">
                                        <i class="fas fa-search me-1"></i>View Details
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    if (container) {
                        container.insertAdjacentHTML('beforeend', recHTML);
                    }
                }
            });
            
            // Update button
            if (btn) {
                if (hasMoreRecommendations) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-arrow-right me-2"></i>Show More Recommendations';
                } else {
                    btn.outerHTML = '<p class="text-center text-muted mt-3"><i class="fas fa-check-circle me-2"></i>No more recommendations available</p>';
                }
            }
            
            // Smooth scroll to new recommendations
            if (newRecommendations.length > 0 && container) {
                const newElements = container.querySelectorAll('.col-md-4');
                if (newElements.length > 0) {
                    newElements[newElements.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        })
        .catch(error => {
            // Show user-friendly error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
            errorDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>Unable to load more recommendations. Please try again.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            const container = document.getElementById('recommendationsSection');
            if (container) container.appendChild(errorDiv);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-arrow-right me-2"></i>Show More Recommendations';
            }
        });
    };

    // Toggle favorite function
    window.toggleFavorite = function(movieId, movieTitle) {
        if (!movieId || movieId === 'N/A') return;
        
        const btn = event.target.closest('.favorite-btn');
        const isFavorite = btn.classList.contains('active');
        
        fetch(isFavorite ? '/remove_favorite' : '/add_favorite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                movie_id: movieId, 
                movie_title: movieTitle 
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                btn.classList.toggle('active');
                btn.innerHTML = `<i class="fas fa-heart"></i> ${btn.classList.contains('active') ? 'Remove from Favorites' : 'Add to Favorites'}`;
                // Show success message briefly
                const flashDiv = document.createElement('div');
                flashDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
                flashDiv.style.zIndex = '9999';
                flashDiv.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.body.appendChild(flashDiv);
                setTimeout(() => flashDiv.remove(), 3000);
            } else {
                // Show error in a more user-friendly way
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
                errorDiv.style.zIndex = '9999';
                errorDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(data.error || 'Failed to update favorites')}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.body.appendChild(errorDiv);
                setTimeout(() => errorDiv.remove(), 5000);
            }
        })
        .catch(error => {
            // Show user-friendly error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
            errorDiv.style.zIndex = '9999';
            errorDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>An error occurred while updating favorites. Please try again.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 5000);
        });
    };

    // Store reference for external access
    window.triggerMovieSearch = function(query) {
        if (searchInput && query) {
            searchInput.value = query;
            searchMovie(query);
        }
    };
});