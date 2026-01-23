/**
 * Barcode Scanner Component
 * 
 * Integrates html5-qrcode library for camera-based and file-based barcode scanning
 * with htmx for server communication and progressive enhancement.
 * 
 * Performance optimizations:
 * - Lazy loading of html5-qrcode library
 * - Camera resource management and cleanup
 * - Mobile performance and battery optimization
 * - Debouncing to prevent multiple simultaneous scans
 */

class BarcodeScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.scanner = null;
        this.isScanning = false;
        this.isProcessing = false; // Debouncing flag
        this.isTogglingCamera = false; // Lock flag for camera toggle operations
        this.libraryLoaded = false;
        this.scanTimeout = null; // For mobile battery optimization
        this.lastScanTime = 0; // Debouncing timestamp
        this.scanCooldown = 2000; // 2 second cooldown between scans
        
        // Basic options that don't depend on the library
        this.baseOptions = {
            fps: this.isMobile() ? 5 : 10, // Lower FPS on mobile for battery
            qrbox: { width: 250, height: 250 },
            // Mobile optimizations
            aspectRatio: this.isMobile() ? 1.0 : 1.777777, // Square on mobile
            disableFlip: this.isMobile(), // Disable flip on mobile for performance
            ...options
        };
        
        // Options that depend on the library will be set after loading
        this.options = null;
        
        this.setupEventListeners();
        this.setupVisibilityHandling();
        this.setupMobileOptimizations();
    }

    /**
     * Detect if running on mobile device
     */
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               window.innerWidth <= 768;
    }

    /**
     * Lazy load the html5-qrcode library
     */
    async loadLibrary() {
        if (this.libraryLoaded || typeof Html5Qrcode !== 'undefined') {
            this.libraryLoaded = true;
            return true;
        }

        try {
            this.showLoading('Loading barcode scanner...');
            
            // Create script element for lazy loading
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
            
            // Wait for script to load
            await new Promise((resolve, reject) => {
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });

            // Wait a bit for the library to initialize
            await new Promise(resolve => setTimeout(resolve, 100));
            
            if (typeof Html5Qrcode === 'undefined' || typeof Html5QrcodeSupportedFormats === 'undefined') {
                throw new Error('Library failed to initialize');
            }

            // Now that the library is loaded, set up the full options
            this.options = {
                ...this.baseOptions,
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39
                ]
            };

            // Apply mobile optimizations now that options are available
            if (this.isMobile() && this.options.fps) {
                this.options.fps = Math.min(this.options.fps, 5);
            }

            this.libraryLoaded = true;
            this.hideLoading();
            return true;
            
        } catch (error) {
            console.error('Failed to load html5-qrcode library:', error);
            this.hideLoading();
            this.showError('Failed to load barcode scanning library. Please refresh the page.');
            return false;
        }
    }

    /**
     * Initialize the barcode scanner (called when needed)
     */
    async init() {
        if (this.scanner) {
            return true; // Already initialized
        }

        try {
            // Lazy load library if not already loaded
            if (!await this.loadLibrary()) {
                return false;
            }

            this.scanner = new Html5Qrcode(this.containerId);
            return true;
            
        } catch (error) {
            console.error('Failed to initialize barcode scanner:', error);
            this.showError('Failed to initialize barcode scanner. Please try refreshing the page.');
            return false;
        }
    }

    /**
     * Setup event listeners for scanner controls
     */
    setupEventListeners() {
        // Start camera button
        const startCameraBtn = document.getElementById('start-camera-btn');
        if (startCameraBtn) {
            startCameraBtn.addEventListener('click', () => this.startCamera());
        }

        // Stop camera button
        const stopCameraBtn = document.getElementById('stop-camera-btn');
        if (stopCameraBtn) {
            stopCameraBtn.addEventListener('click', () => this.stopCamera());
        }

        // File input for file-based scanning
        const fileInput = document.getElementById('barcode-file-input');
        const mainFileInput = document.getElementById('barcode-file-input-main');
        
        if (fileInput) {
            fileInput.addEventListener('change', (event) => this.handleFileSelect(event));
        }
        
        if (mainFileInput) {
            mainFileInput.addEventListener('change', (event) => this.handleFileSelect(event));
        }

        // Manual ISBN entry fallback
        const manualEntryBtn = document.getElementById('manual-entry-btn');
        if (manualEntryBtn) {
            manualEntryBtn.addEventListener('click', () => this.showManualEntry());
        }
    }

    /**
     * Setup visibility change handling for battery optimization
     */
    setupVisibilityHandling() {
        // Stop camera when page becomes hidden to save battery
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isScanning) {
                this.pauseScanning();
            } else if (!document.hidden && this.scanner && !this.isScanning) {
                // Optionally resume scanning when page becomes visible
                // For now, just show the start button
                this.updateUI('stopped');
            }
        });

        // Handle page focus/blur for additional battery optimization
        window.addEventListener('blur', () => {
            if (this.isScanning) {
                this.pauseScanning();
            }
        });
    }

    /**
     * Setup mobile-specific optimizations
     */
    setupMobileOptimizations() {
        if (this.isMobile()) {
            // Auto-stop scanning after 2 minutes on mobile to save battery
            this.maxScanTime = 2 * 60 * 1000; // 2 minutes
            
            // Reduce scan frequency on mobile (only if options are available)
            if (this.options && this.options.fps) {
                this.options.fps = Math.min(this.options.fps, 5);
            }
            
            // Add touch event optimizations
            document.addEventListener('touchstart', () => {
                // Prevent accidental touches during scanning
                if (this.isScanning) {
                    // Could add haptic feedback here if needed
                }
            }, { passive: true });
        }
    }

    /**
     * Pause scanning (for visibility changes)
     */
    pauseScanning() {
        if (this.isScanning && this.scanner) {
            this.scanner.pause();
        }
    }

    /**
     * Resume scanning
     */
    resumeScanning() {
        if (this.scanner && !this.isScanning) {
            this.scanner.resume();
        }
    }

    /**
     * Start camera scanning with enhanced resource management
     */
    async startCamera() {
        if (this.isScanning || this.isProcessing || this.isTogglingCamera) {
            return;
        }

        this.isTogglingCamera = true;

        // Initialize scanner if not already done
        if (!await this.init()) {
            this.isTogglingCamera = false;
            return;
        }

        try {
            this.showLoading('Starting camera...');
            
            // Get available cameras
            const cameras = await Html5Qrcode.getCameras();
            if (cameras.length === 0) {
                throw new Error('No cameras found on this device');
            }

            // Use back camera if available, otherwise use first camera
            const cameraId = cameras.find(camera => 
                camera.label.toLowerCase().includes('back') || 
                camera.label.toLowerCase().includes('rear')
            )?.id || cameras[0].id;

            // Start scanning with mobile-optimized config
            await this.scanner.start(
                cameraId,
                this.options,
                (decodedText, decodedResult) => this.onScanSuccess(decodedText, decodedResult),
                (errorMessage) => this.onScanError(errorMessage)
            );

            this.isScanning = true;
            this.updateUI('scanning');
            this.hideLoading();

            // Set up auto-stop timer for mobile battery optimization
            if (this.isMobile() && this.maxScanTime) {
                this.scanTimeout = setTimeout(() => {
                    this.stopCamera();
                    this.showError('Scanning stopped to save battery. Tap "Start Camera" to continue.', true);
                }, this.maxScanTime);
            }

            this.isTogglingCamera = false;

        } catch (error) {
            console.error('Camera start error:', error);
            this.handleCameraError(error);
            this.isTogglingCamera = false;
        }
    }

    /**
     * Stop camera scanning with proper resource cleanup
     */
    async stopCamera() {
        if (!this.isScanning || this.isTogglingCamera) {
            return;
        }

        this.isTogglingCamera = true;

        try {
            // Clear any timeouts
            if (this.scanTimeout) {
                clearTimeout(this.scanTimeout);
                this.scanTimeout = null;
            }

            // Stop the scanner
            if (this.scanner) {
                await this.scanner.stop();
            }

            this.isScanning = false;
            this.updateUI('stopped');
            
        } catch (error) {
            console.error('Error stopping camera:', error);
            // Force cleanup even if stop() fails
            this.isScanning = false;
            this.updateUI('stopped');
        } finally {
            this.isTogglingCamera = false;
        }
    }

    /**
     * Handle successful barcode scan with debouncing
     */
    onScanSuccess(decodedText, decodedResult, scanType = 'camera') {
        const now = Date.now();
        
        // Debouncing: prevent multiple scans within cooldown period
        // Ignore cooldown for file scans as they are explicit user actions
        const checkCooldown = scanType !== 'file';
        if (this.isProcessing || (checkCooldown && (now - this.lastScanTime) < this.scanCooldown)) {
            return;
        }

        this.isProcessing = true;
        this.lastScanTime = now;
        
        console.log('Barcode scanned:', decodedText);
        
        // Stop camera scanning if it was camera scan (don't stop for file scans)
        if (scanType === 'camera') {
            this.stopCamera();
        }
        
        // Show processing indicator
        this.showLoading('Processing barcode...');
        
        // Send scanned result to server via htmx
        this.sendToServer(decodedText, scanType);
    }

    /**
     * Handle scan errors (not critical - scanning continues)
     */
    onScanError(errorMessage) {
        // Don't log every scan attempt - only log actual errors
        if (!errorMessage.includes('No MultiFormat Readers') && 
            !errorMessage.includes('NotFoundException')) {
            console.warn('Scan error:', errorMessage);
        }
    }

    /**
     * Handle file selection for file-based scanning with enhanced validation
     */
    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // Prevent multiple file processing
        if (this.isProcessing) {
            return;
        }

        this.isProcessing = true;

        // Enhanced file validation
        const validationResult = this.validateFile(file);
        if (!validationResult.valid) {
            this.isProcessing = false;
            this.sendErrorToServer(
                validationResult.errorType,
                validationResult.message,
                'low',
                {
                    show_retry: true,
                    show_manual_entry: true,
                    show_file_fallback: false
                }
            );
            return;
        }

        try {
            // Initialize scanner if not already done
            if (!await this.init()) {
                this.isProcessing = false;
                return;
            }

            this.showLoading('Processing image...');
            
            // Scan the file
            const decodedText = await this.scanner.scanFile(file, true);
            
            // Reset processing flag to allow onScanSuccess to proceed
            this.isProcessing = false;
            this.onScanSuccess(decodedText, null, 'file');
            
        } catch (error) {
            console.error('File scan error:', error);
            this.isProcessing = false;
            this.sendErrorToServer(
                'barcode_detection_error',
                'Could not detect a barcode in this image.',
                'low',
                {
                    show_retry: true,
                    show_file_fallback: false,
                    show_manual_entry: true
                }
            );
        }
    }

    /**
     * Validate file for scanning with detailed error categorization
     */
    validateFile(file) {
        // Check file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            return {
                valid: false,
                errorType: 'file_format_error',
                message: 'Please select a valid image file (JPEG, PNG, or WebP).'
            };
        }

        // Check file size (max 10MB, but recommend smaller on mobile)
        const maxSize = this.isMobile() ? 5 * 1024 * 1024 : 10 * 1024 * 1024; // 5MB on mobile, 10MB on desktop
        if (file.size > maxSize) {
            const sizeMB = Math.round(file.size / (1024 * 1024));
            const maxMB = Math.round(maxSize / (1024 * 1024));
            return {
                valid: false,
                errorType: 'file_size_error',
                message: `File size too large (${sizeMB}MB). Please select an image smaller than ${maxMB}MB.`
            };
        }

        return { valid: true };
    }

    /**
     * Send scanned barcode to server with enhanced error handling
     */
    sendToServer(scannedText, scanType) {
        // Use htmx to send the data to the server
        htmx.ajax('POST', '/scan/process', {
            values: { 
                scanned_text: scannedText, 
                scan_type: scanType 
            },
            target: '#scan-result-container',
            swap: 'innerHTML'
        }).then(() => {
            this.hideLoading();
            this.isProcessing = false;
        }).catch((error) => {
            console.error('Server communication error:', error);
            this.hideLoading();
            this.isProcessing = false;
            
            // Determine if this is a network error
            const isNetworkError = !navigator.onLine || 
                                 error.message.includes('NetworkError') ||
                                 error.message.includes('Failed to fetch');
            
            if (isNetworkError) {
                this.sendErrorToServer(
                    'network_error',
                    'Unable to connect to the book information service. Please check your internet connection.',
                    'medium',
                    {
                        show_retry: true,
                        show_manual_entry: true,
                        show_file_fallback: false
                    }
                );
            } else {
                this.sendErrorToServer(
                    'unknown_error',
                    'Failed to process barcode. Please try again.',
                    'medium',
                    {
                        show_retry: true,
                        show_manual_entry: true,
                        show_file_fallback: true
                    }
                );
            }
        });
    }

    /**
     * Handle camera permission and initialization errors with enhanced error categorization
     */
    handleCameraError(error) {
        this.hideLoading();
        this.isProcessing = false;
        
        let errorType = 'camera_error';
        let errorMessage = 'Camera access failed. ';
        let showFileOption = true;
        let severity = 'medium';

        // Categorize the error for better handling
        if (error.name === 'NotAllowedError' || error.message.includes('Permission denied')) {
            errorType = 'camera_permission_error';
            errorMessage = 'Camera access is required to scan barcodes. Please allow camera access and try again.';
            severity = 'medium';
        } else if (error.name === 'NotFoundError' || error.message.includes('No cameras found')) {
            errorType = 'camera_not_found_error';
            errorMessage = 'No camera was found on this device.';
            severity = 'medium';
        } else if (error.name === 'NotSupportedError') {
            errorType = 'camera_not_supported_error';
            errorMessage = 'Camera scanning is not supported in this browser.';
            severity = 'medium';
        } else if (error.message.includes('HTTPS')) {
            errorType = 'camera_not_supported_error';
            errorMessage = 'Camera access requires a secure connection (HTTPS).';
            severity = 'high';
        } else {
            errorType = 'unknown_error';
            errorMessage = 'An unexpected camera error occurred.';
            severity = 'high';
        }

        // Send structured error to server for consistent handling
        this.sendErrorToServer(errorType, errorMessage, severity, {
            show_file_fallback: showFileOption,
            show_manual_entry: true,
            show_retry: errorType !== 'camera_not_found_error'
        });

        this.updateUI('error');
    }

    /**
     * Send structured error information to server for consistent error handling
     */
    sendErrorToServer(errorType, errorMessage, severity = 'medium', options = {}) {
        const errorData = {
            error_type: errorType,
            error_message: errorMessage,
            severity: severity,
            suggested_action: this.getSuggestedAction(errorType),
            ...options
        };

        // Use htmx to render the enhanced error message
        htmx.ajax('POST', '/scan/process', {
            values: { 
                scanned_text: '', 
                scan_type: 'camera',
                error_data: JSON.stringify(errorData)
            },
            target: '#scan-result-container',
            swap: 'innerHTML'
        }).catch((error) => {
            console.error('Failed to send error to server:', error);
            // Fallback to local error display
            this.showLocalError(errorMessage, options);
        });
    }

    /**
     * Get suggested action for error type
     */
    getSuggestedAction(errorType) {
        const actions = {
            'camera_permission_error': 'Allow camera access in your browser settings, or use the file upload option.',
            'camera_not_found_error': 'Use the file upload option to scan an image of the barcode.',
            'camera_not_supported_error': 'Use the file upload option or enter the ISBN manually.',
            'network_error': 'Check your internet connection and try again, or enter the ISBN manually.',
            'barcode_detection_error': 'Ensure good lighting and hold the barcode steady, or try uploading a clearer image.',
            'file_format_error': 'Select a JPEG, PNG, or WebP image file.',
            'file_size_error': 'Reduce the image size or select a different image.',
            'unknown_error': 'Please try again or contact support if the problem persists.'
        };
        
        return actions[errorType] || 'Please try again or contact support.';
    }

    /**
     * Show local error message as fallback
     */
    showLocalError(message, options = {}) {
        const errorEl = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');
        const fileOptionEl = document.getElementById('file-option');
        
        if (errorEl) {
            errorEl.style.display = 'block';
        }
        if (errorText) {
            errorText.textContent = message;
        }
        if (fileOptionEl) {
            fileOptionEl.style.display = options.show_file_fallback ? 'block' : 'none';
        }
    }

    /**
     * Show loading indicator
     */
    showLoading(message = 'Loading...') {
        const loadingEl = document.getElementById('loading-indicator');
        const loadingText = document.getElementById('loading-text');
        
        if (loadingEl) {
            loadingEl.style.display = 'block';
        }
        if (loadingText) {
            loadingText.textContent = message;
        }
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        const loadingEl = document.getElementById('loading-indicator');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    /**
     * Show error message
     */
    showError(message, showFileOption = false) {
        const errorEl = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');
        const fileOptionEl = document.getElementById('file-option');
        
        if (errorEl) {
            errorEl.style.display = 'block';
        }
        if (errorText) {
            errorText.textContent = message;
        }
        if (fileOptionEl) {
            fileOptionEl.style.display = showFileOption ? 'block' : 'none';
        }
    }

    /**
     * Hide error message
     */
    hideError() {
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    /**
     * Update UI based on scanner state
     */
    updateUI(state) {
        const startBtn = document.getElementById('start-camera-btn');
        const stopBtn = document.getElementById('stop-camera-btn');
        const fileSection = document.getElementById('file-scan-section');
        
        switch (state) {
            case 'scanning':
                if (startBtn) startBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-block';
                if (fileSection) fileSection.style.display = 'none';
                this.hideError();
                break;
                
            case 'stopped':
                if (startBtn) startBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'none';
                if (fileSection) fileSection.style.display = 'block';
                break;
                
            case 'error':
                if (startBtn) startBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'none';
                if (fileSection) fileSection.style.display = 'block';
                break;
        }
    }

    /**
     * Show manual ISBN entry form
     */
    showManualEntry() {
        // Redirect to manual entry or show inline form
        window.location.href = '/';
    }

    /**
     * Cleanup scanner resources with enhanced cleanup
     */
    destroy() {
        // Clear any timeouts
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }

        // Stop camera if running
        if (this.isScanning) {
            this.stopCamera();
        }

        // Clear scanner instance
        if (this.scanner) {
            try {
                this.scanner.clear();
            } catch (error) {
                console.warn('Error clearing scanner:', error);
            }
            this.scanner = null;
        }

        // Reset flags
        this.isScanning = false;
        this.isProcessing = false;
        this.libraryLoaded = false;
    }
}

// Initialize scanner when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the scanner page
    const scannerContainer = document.getElementById('barcode-reader');
    if (scannerContainer) {
        // Initialize the scanner (library will be loaded lazily)
        window.barcodeScanner = new BarcodeScanner('barcode-reader');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.barcodeScanner) {
        window.barcodeScanner.destroy();
    }
});

// Additional cleanup for mobile battery optimization
window.addEventListener('pagehide', function() {
    if (window.barcodeScanner) {
        window.barcodeScanner.destroy();
    }
});

// Handle orientation changes on mobile
window.addEventListener('orientationchange', function() {
    if (window.barcodeScanner && window.barcodeScanner.isScanning) {
        // Restart scanner after orientation change for better performance
        setTimeout(() => {
            if (window.barcodeScanner) {
                window.barcodeScanner.stopCamera().then(() => {
                    // Give time for orientation to settle
                    setTimeout(() => {
                        if (window.barcodeScanner) {
                            window.barcodeScanner.startCamera();
                        }
                    }, 500);
                });
            }
        }, 100);
    }
});