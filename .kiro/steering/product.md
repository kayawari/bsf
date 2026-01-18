---
inclusion: always
---

# Product Overview

## Book Management Application

A Flask-based web application for managing personal book collections by manually inputting ISBN numbers and retrieving book information from the Google Books API.

### Core Features

- **ISBN-based Book Entry**: Users input ISBN numbers to add books to their collection
- **Google Books API Integration**: Automatically fetches book metadata (title, authors, publisher, description, cover images)
- **Graceful Fallback**: Creates book records with basic information when API is unavailable
- **Progressive Enhancement**: Works without JavaScript, enhanced with htmx for better UX
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices

### Key User Flows

1. **Add Book**: Enter ISBN → Validate → Fetch metadata → Store in collection
2. **View Collection**: Browse all books with cover images and basic info
3. **Book Details**: View detailed information for individual books
4. **Refresh Metadata**: Update book information from API when needed

### Technical Approach

- **Resilient Design**: Handles external API failures gracefully with fallback data
- **UTF-8 Support**: Full Unicode character support for international books
- **Instance Configuration**: Secure configuration management for production deployment
- **Property-based Testing**: Uses Hypothesis for robust test coverage