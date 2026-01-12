"""
Property-based tests for responsive design functionality.

Feature: book-management, Property 23: Desktop Layout Display
Feature: book-management, Property 24: Tablet Layout Adaptation  
Feature: book-management, Property 25: Mobile Layout Optimization
Feature: book-management, Property 26: Responsive Layout Adjustment
Feature: book-management, Property 27: Mobile Detail View Stacking
Feature: book-management, Property 28: Touch Interface Sizing
"""

import pytest
import re
from hypothesis import given, strategies as st, settings, HealthCheck
from app import create_app, db
from app.models.book import Book


def create_test_app():
    """Create and configure test app."""
    app = create_app('testing')
    return app


class TestDesktopLayoutDisplay:
    """
    Property-based tests for desktop layout display.
    Feature: book-management, Property 23: Desktop Layout Display
    """
    
    @given(
        books_count=st.integers(min_value=0, max_value=20),
        viewport_width=st.integers(min_value=1024, max_value=2560)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_layout_displays_properly(self, books_count, viewport_width):
        """
        **Property 23: Desktop Layout Display**
        *For any* desktop screen size (1024px and wider), the application should 
        display properly with appropriate layout and spacing.
        **Validates: Requirements 9.1**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create test books with unique ISBNs
                for i in range(books_count):
                    # Generate unique ISBN by using i directly and padding
                    isbn_suffix = str(i).zfill(3)[-3:]  # Last 3 digits, padded
                    isbn = f"97803064061{isbn_suffix}"
                    book = Book(
                        isbn=isbn,
                        title=f"Test Book {i}",
                        authors=[f"Author {i}"],
                        publisher=f"Publisher {i}"
                    )
                    db.session.add(book)
                db.session.commit()
                
                # Get the main page
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify desktop layout elements are present
                assert 'container' in html_content
                assert 'book-grid' in html_content
                assert 'isbn-input-section' in html_content
                assert 'collection-section' in html_content
                
                # Verify CSS contains desktop-appropriate styles
                css_response = client.get('/static/css/style.css')
                assert css_response.status_code == 200
                css_content = css_response.data.decode('utf-8')
                
                # Desktop layout should have grid with minmax(280px, 1fr)
                assert 'grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))' in css_content
                
                # Desktop should have proper container max-width
                assert 'max-width: 1200px' in css_content
                
                # Verify responsive meta tag is present for proper viewport handling
                assert 'viewport' in html_content
                assert 'width=device-width' in html_content
                
            finally:
                db.drop_all()
    
    @given(
        book_title=st.text(min_size=1, max_size=100),
        book_authors=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_book_detail_layout(self, book_title, book_authors):
        """
        **Property 23: Desktop Layout Display**
        *For any* book detail view on desktop, the layout should display with 
        proper two-column grid structure.
        **Validates: Requirements 9.1**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book
                book = Book(
                    isbn="9780306406157",
                    title=book_title,
                    authors=book_authors,
                    description="Test description"
                )
                db.session.add(book)
                db.session.commit()
                
                # Get book detail page
                response = client.get(f'/book/{book.id}')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify desktop detail layout elements
                assert 'book-detail-content' in html_content
                assert 'book-cover' in html_content
                assert 'book-metadata' in html_content
                
                # Verify CSS has desktop two-column grid
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Desktop detail should use two-column grid
                assert 'grid-template-columns: auto 1fr' in css_content
                
            finally:
                db.drop_all()


class TestTabletLayoutAdaptation:
    """
    Property-based tests for tablet layout adaptation.
    Feature: book-management, Property 24: Tablet Layout Adaptation
    """
    
    @given(
        books_count=st.integers(min_value=0, max_value=15),
        viewport_width=st.integers(min_value=768, max_value=1023)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tablet_layout_adaptation(self, books_count, viewport_width):
        """
        **Property 24: Tablet Layout Adaptation**
        *For any* tablet screen size (768px to 1023px), the application should 
        adapt its layout appropriately for the viewport.
        **Validates: Requirements 9.2**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create test books with unique ISBNs
                for i in range(books_count):
                    isbn_suffix = str(i).zfill(3)[-3:]
                    isbn = f"97803064061{isbn_suffix}"
                    book = Book(
                        isbn=isbn,
                        title=f"Test Book {i}",
                        authors=[f"Author {i}"]
                    )
                    db.session.add(book)
                db.session.commit()
                
                # Get the main page
                response = client.get('/')
                assert response.status_code == 200
                
                # Verify CSS contains tablet-specific media queries
                css_response = client.get('/static/css/style.css')
                assert css_response.status_code == 200
                css_content = css_response.data.decode('utf-8')
                
                # Tablet media query should exist
                tablet_media_query = '@media (max-width: 1023px) and (min-width: 768px)'
                assert tablet_media_query in css_content
                
                # Tablet should have adjusted grid columns
                # Look for the tablet-specific grid template
                tablet_section = css_content[css_content.find(tablet_media_query):]
                next_media_query = tablet_section.find('@media', 1)
                if next_media_query != -1:
                    tablet_section = tablet_section[:next_media_query]
                
                assert 'minmax(250px, 1fr)' in tablet_section
                
                # Tablet should have reduced padding
                assert 'padding: 15px' in tablet_section
                
            finally:
                db.drop_all()
    
    @given(
        book_title=st.text(min_size=1, max_size=80),
        has_cover=st.booleans()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tablet_book_detail_adaptation(self, book_title, has_cover):
        """
        **Property 24: Tablet Layout Adaptation**
        *For any* book detail view on tablet, the layout should adapt with 
        smaller cover images and adjusted spacing.
        **Validates: Requirements 9.2**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book
                book = Book(
                    isbn="9780306406157",
                    title=book_title,
                    cover_image_url="http://example.com/cover.jpg" if has_cover else None
                )
                db.session.add(book)
                db.session.commit()
                
                # Get book detail page
                response = client.get(f'/book/{book.id}')
                assert response.status_code == 200
                
                # Verify CSS has tablet adaptations for detail view
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Find tablet media query section
                tablet_media_query = '@media (max-width: 1023px) and (min-width: 768px)'
                tablet_section = css_content[css_content.find(tablet_media_query):]
                next_media_query = tablet_section.find('@media', 1)
                if next_media_query != -1:
                    tablet_section = tablet_section[:next_media_query]
                
                # Tablet should have smaller cover images
                assert 'max-width: 150px' in tablet_section
                assert 'max-height: 225px' in tablet_section
                
                # Tablet should have adjusted padding
                assert 'padding: 1.5rem' in tablet_section
                
            finally:
                db.drop_all()


class TestMobileLayoutOptimization:
    """
    Property-based tests for mobile layout optimization.
    Feature: book-management, Property 25: Mobile Layout Optimization
    """
    
    @given(
        books_count=st.integers(min_value=0, max_value=10),
        viewport_width=st.integers(min_value=320, max_value=767)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_mobile_layout_optimization(self, books_count, viewport_width):
        """
        **Property 25: Mobile Layout Optimization**
        *For any* mobile screen size (767px and smaller), the application should 
        provide an optimized layout for the smaller viewport.
        **Validates: Requirements 9.3**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create test books with unique ISBNs
                for i in range(books_count):
                    isbn_suffix = str(i).zfill(3)[-3:]
                    isbn = f"97803064061{isbn_suffix}"
                    book = Book(
                        isbn=isbn,
                        title=f"Test Book {i}",
                        authors=[f"Author {i}"]
                    )
                    db.session.add(book)
                db.session.commit()
                
                # Get the main page
                response = client.get('/')
                assert response.status_code == 200
                
                # Verify CSS contains mobile-specific optimizations
                css_response = client.get('/static/css/style.css')
                assert css_response.status_code == 200
                css_content = css_response.data.decode('utf-8')
                
                # Mobile media query should exist
                mobile_media_query = '@media (max-width: 767px)'
                assert mobile_media_query in css_content
                
                # Find mobile section
                mobile_section = css_content[css_content.find(mobile_media_query):]
                next_media_query = mobile_section.find('@media', 1)
                if next_media_query != -1:
                    mobile_section = mobile_section[:next_media_query]
                
                # Mobile should have single column grid
                assert 'grid-template-columns: 1fr' in mobile_section
                
                # Mobile should have stacked input form
                assert 'flex-direction: column' in mobile_section
                
                # Mobile should have reduced padding
                assert 'padding: 10px' in mobile_section
                
            finally:
                db.drop_all()
    
    @given(
        form_input=st.text(min_size=1, max_size=20).filter(lambda x: x.isdigit())
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_mobile_form_optimization(self, form_input):
        """
        **Property 25: Mobile Layout Optimization**
        *For any* form interaction on mobile, the input elements should be 
        optimized for touch with proper sizing and stacking.
        **Validates: Requirements 9.3**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Get the main page with form
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify form elements are present
                assert 'isbn-input' in html_content
                assert 'add-button' in html_content
                
                # Verify CSS has mobile form optimizations
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Find mobile section
                mobile_media_query = '@media (max-width: 767px)'
                mobile_section = css_content[css_content.find(mobile_media_query):]
                next_media_query = mobile_section.find('@media', 1)
                if next_media_query != -1:
                    mobile_section = mobile_section[:next_media_query]
                
                # Mobile should have larger touch targets
                assert 'min-height: 48px' in mobile_section
                
                # Mobile form should stack vertically
                assert 'flex-direction: column' in mobile_section
                
            finally:
                db.drop_all()


class TestResponsiveLayoutAdjustment:
    """
    Property-based tests for responsive layout adjustment.
    Feature: book-management, Property 26: Responsive Layout Adjustment
    """
    
    @given(
        screen_sizes=st.lists(
            st.integers(min_value=320, max_value=2560),
            min_size=2,
            max_size=5
        ).map(sorted),
        books_count=st.integers(min_value=1, max_value=8)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_responsive_layout_adjustment_across_sizes(self, screen_sizes, books_count):
        """
        **Property 26: Responsive Layout Adjustment**
        *For any* screen size change, the book collection display should adjust 
        its layout accordingly to maintain usability.
        **Validates: Requirements 9.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create test books with unique ISBNs
                for i in range(books_count):
                    isbn_suffix = str(i).zfill(3)[-3:]
                    isbn = f"97803064061{isbn_suffix}"
                    book = Book(
                        isbn=isbn,
                        title=f"Test Book {i}",
                        authors=[f"Author {i}"]
                    )
                    db.session.add(book)
                db.session.commit()
                
                # Get the CSS to analyze responsive breakpoints
                css_response = client.get('/static/css/style.css')
                assert css_response.status_code == 200
                css_content = css_response.data.decode('utf-8')
                
                # Verify all major responsive breakpoints exist
                breakpoints = [
                    '@media (max-width: 767px)',      # Mobile
                    '@media (max-width: 1023px) and (min-width: 768px)',  # Tablet
                    '@media (max-width: 480px)'       # Very small mobile
                ]
                
                for breakpoint in breakpoints:
                    assert breakpoint in css_content, f"Missing responsive breakpoint: {breakpoint}"
                
                # Verify different grid configurations for different sizes
                # Desktop: minmax(280px, 1fr)
                # Tablet: minmax(250px, 1fr) 
                # Mobile: 1fr (single column)
                
                grid_configs = [
                    'minmax(280px, 1fr)',  # Desktop
                    'minmax(250px, 1fr)',  # Tablet
                    'grid-template-columns: 1fr'  # Mobile
                ]
                
                for config in grid_configs:
                    assert config in css_content, f"Missing grid configuration: {config}"
                
                # Verify touch-friendly sizing exists
                assert 'min-height: 44px' in css_content  # Standard touch target
                assert 'min-height: 48px' in css_content  # Mobile touch target
                
            finally:
                db.drop_all()
    
    @given(
        viewport_transitions=st.lists(
            st.tuples(
                st.integers(min_value=320, max_value=2560),  # from_width
                st.integers(min_value=320, max_value=2560)   # to_width
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_layout_consistency_across_viewport_changes(self, viewport_transitions):
        """
        **Property 26: Responsive Layout Adjustment**
        *For any* viewport size transition, the layout should maintain structural 
        consistency and proper element relationships.
        **Validates: Requirements 9.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book
                book = Book(
                    isbn="9780306406157",
                    title="Test Book",
                    authors=["Test Author"]
                )
                db.session.add(book)
                db.session.commit()
                
                # Get the main page
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify core structural elements are always present
                core_elements = [
                    'container',
                    'app-header',
                    'isbn-input-section',
                    'collection-section',
                    'book-grid'
                ]
                
                for element in core_elements:
                    assert element in html_content, f"Missing core element: {element}"
                
                # Verify CSS maintains proper hierarchy across all breakpoints
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # All breakpoints should maintain container structure
                media_queries = re.findall(r'@media[^{]+{[^}]+}', css_content, re.DOTALL)
                
                # Each media query should maintain usable layout
                for media_query in media_queries:
                    # Should not break fundamental layout structure
                    # Verify no negative margins or extreme values that would break layout
                    assert 'margin: -' not in media_query
                    assert 'padding: -' not in media_query
                
            finally:
                db.drop_all()


class TestMobileDetailViewStacking:
    """
    Property-based tests for mobile detail view stacking.
    Feature: book-management, Property 27: Mobile Detail View Stacking
    """
    
    @given(
        book_title=st.text(min_size=1, max_size=100),
        book_description=st.one_of(st.none(), st.text(min_size=10, max_size=500)),
        has_cover=st.booleans()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_mobile_detail_view_stacking(self, book_title, book_description, has_cover):
        """
        **Property 27: Mobile Detail View Stacking**
        *For any* book detail view on mobile devices, information should be 
        stacked vertically for better readability.
        **Validates: Requirements 9.5**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book
                book = Book(
                    isbn="9780306406157",
                    title=book_title,
                    description=book_description,
                    cover_image_url="http://example.com/cover.jpg" if has_cover else None,
                    authors=["Test Author"],
                    publisher="Test Publisher"
                )
                db.session.add(book)
                db.session.commit()
                
                # Get book detail page
                response = client.get(f'/book/{book.id}')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify detail view elements are present
                assert 'book-detail-content' in html_content
                assert 'book-cover' in html_content
                assert 'book-metadata' in html_content
                
                # Verify CSS has mobile stacking for detail view
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Find mobile section
                mobile_media_query = '@media (max-width: 767px)'
                mobile_section = css_content[css_content.find(mobile_media_query):]
                next_media_query = mobile_section.find('@media', 1)
                if next_media_query != -1:
                    mobile_section = mobile_section[:next_media_query]
                
                # Mobile detail should stack vertically (single column)
                assert 'grid-template-columns: 1fr' in mobile_section
                
                # Mobile should center cover image
                assert 'text-align: center' in mobile_section
                
                # Mobile should have appropriate cover sizing
                assert 'max-width: 160px' in mobile_section
                assert 'max-height: 240px' in mobile_section
                
            finally:
                db.drop_all()
    
    @given(
        metadata_fields=st.lists(
            st.sampled_from(['title', 'authors', 'publisher', 'description']),
            min_size=1,
            max_size=4,
            unique=True
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_mobile_metadata_stacking_order(self, metadata_fields):
        """
        **Property 27: Mobile Detail View Stacking**
        *For any* combination of book metadata fields, the mobile layout should 
        stack them in a logical, readable order.
        **Validates: Requirements 9.5**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create book with selected metadata
                book_data = {
                    'isbn': "9780306406157",
                    'title': "Test Title" if 'title' in metadata_fields else None,
                    'authors': ["Test Author"] if 'authors' in metadata_fields else None,
                    'publisher': "Test Publisher" if 'publisher' in metadata_fields else None,
                    'description': "Test description" if 'description' in metadata_fields else None
                }
                
                book = Book(**{k: v for k, v in book_data.items() if v is not None})
                db.session.add(book)
                db.session.commit()
                
                # Get book detail page
                response = client.get(f'/book/{book.id}')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify metadata elements appear in proper order
                if 'title' in metadata_fields:
                    assert 'detail-title' in html_content
                if 'authors' in metadata_fields:
                    assert 'detail-authors' in html_content
                if 'publisher' in metadata_fields:
                    assert 'detail-publisher' in html_content
                if 'description' in metadata_fields:
                    assert 'detail-description' in html_content
                
                # Verify mobile CSS maintains readable text alignment
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                mobile_media_query = '@media (max-width: 767px)'
                mobile_section = css_content[css_content.find(mobile_media_query):]
                
                # Mobile metadata should be left-aligned for readability
                assert 'text-align: left' in mobile_section
                
            finally:
                db.drop_all()


class TestTouchInterfaceSizing:
    """
    Property-based tests for touch interface sizing.
    Feature: book-management, Property 28: Touch Interface Sizing
    """
    
    @given(
        interactive_elements=st.lists(
            st.sampled_from(['button', 'link', 'input']),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_touch_interface_sizing(self, interactive_elements):
        """
        **Property 28: Touch Interface Sizing**
        *For any* interactive element on mobile devices, the element should be 
        appropriately sized for touch interfaces (minimum 44px touch targets).
        **Validates: Requirements 9.6**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book for link testing
                if 'link' in interactive_elements:
                    book = Book(
                        isbn="9780306406157",
                        title="Test Book",
                        authors=["Test Author"]
                    )
                    db.session.add(book)
                    db.session.commit()
                
                # Get the main page
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify interactive elements are present
                if 'button' in interactive_elements:
                    assert 'add-button' in html_content
                if 'input' in interactive_elements:
                    assert 'isbn-input' in html_content
                if 'link' in interactive_elements:
                    assert 'book-title' in html_content
                
                # Verify CSS has proper touch sizing
                css_response = client.get('/static/css/style.css')
                assert css_response.status_code == 200
                css_content = css_response.data.decode('utf-8')
                
                # Standard touch targets should be at least 44px
                assert 'min-height: 44px' in css_content
                
                # Mobile touch targets should be larger (48px)
                mobile_media_query = '@media (max-width: 767px)'
                if mobile_media_query in css_content:
                    mobile_section = css_content[css_content.find(mobile_media_query):]
                    assert 'min-height: 48px' in mobile_section
                
                # Touch device specific media query should exist
                touch_media_query = '@media (hover: none) and (pointer: coarse)'
                assert touch_media_query in css_content
                
            finally:
                db.drop_all()
    
    @given(
        button_types=st.lists(
            st.sampled_from(['add-button', 'back-button', 'refresh-button']),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_button_touch_sizing_consistency(self, button_types):
        """
        **Property 28: Touch Interface Sizing**
        *For any* button element, the touch target should meet minimum size 
        requirements consistently across the application.
        **Validates: Requirements 9.6**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create test book for detail page buttons
                if 'back-button' in button_types or 'refresh-button' in button_types:
                    book = Book(
                        isbn="9780306406157",
                        title="Test Book"
                    )
                    db.session.add(book)
                    db.session.commit()
                    
                    # Get book detail page
                    detail_response = client.get(f'/book/{book.id}')
                    assert detail_response.status_code == 200
                
                # Get main page for add button
                if 'add-button' in button_types:
                    main_response = client.get('/')
                    assert main_response.status_code == 200
                
                # Verify CSS has consistent button sizing
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Get fragment content for refresh button styles
                fragment_content = ""
                if 'refresh-button' in button_types:
                    fragment_response = client.get(f'/book/{book.id}')
                    fragment_content = fragment_response.data.decode('utf-8')
                
                # All buttons should have minimum touch target size
                button_selectors = []
                if 'add-button' in button_types:
                    button_selectors.append('.add-button')
                if 'back-button' in button_types:
                    button_selectors.append('.back-button')
                if 'refresh-button' in button_types:
                    button_selectors.append('.refresh-button')
                
                # Verify each button type has proper sizing
                for selector in button_selectors:
                    # Button should exist in CSS or fragment content
                    if selector == '.refresh-button':
                        assert selector in fragment_content, f"Button selector {selector} not found in fragment"
                    else:
                        assert selector in css_content, f"Button selector {selector} not found in CSS"
                
                # Verify minimum touch target sizes are defined
                assert 'min-height: 44px' in css_content
                
                # Verify touch device optimizations
                touch_media_query = '@media (hover: none) and (pointer: coarse)'
                if touch_media_query in css_content:
                    touch_section = css_content[css_content.find(touch_media_query):]
                    # Touch devices should have larger targets
                    assert 'min-height: 48px' in touch_section
                
            finally:
                db.drop_all()
    
    @given(
        link_text=st.text(min_size=1, max_size=50),
        has_padding=st.booleans()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_link_touch_area_sizing(self, link_text, has_padding):
        """
        **Property 28: Touch Interface Sizing**
        *For any* link element, the touch area should be appropriately sized 
        for touch interaction, even if the text is small.
        **Validates: Requirements 9.6**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Create a test book with the given title
                book = Book(
                    isbn="9780306406157",
                    title=link_text,
                    authors=["Test Author"]
                )
                db.session.add(book)
                db.session.commit()
                
                # Get the main page with book links
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.data.decode('utf-8')
                
                # Verify book title link is present
                assert 'book-title' in html_content
                
                # Verify CSS provides adequate touch area for links
                css_response = client.get('/static/css/style.css')
                css_content = css_response.data.decode('utf-8')
                
                # Links should have touch-friendly styling
                book_title_css = '.book-title a'
                assert book_title_css in css_content
                
                # Touch device media query should enhance link touch areas
                touch_media_query = '@media (hover: none) and (pointer: coarse)'
                if touch_media_query in css_content:
                    touch_section = css_content[css_content.find(touch_media_query):]
                    # Touch devices should have padding for larger touch areas
                    assert 'padding:' in touch_section and 'book-title a' in touch_section
                
                # Focus styles should be present for accessibility
                assert ':focus' in css_content
                
            finally:
                db.drop_all()