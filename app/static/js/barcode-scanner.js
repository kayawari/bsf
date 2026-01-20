/**
 * Barcode Scanner Component
 * 
 * Integrates html5-qrcode library for camera-based and file-based barcode scanning
 * with htmx for server communication and progressive enhancement.
 */

class BarcodeScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.scanner = null;
        this.isScanning = false;
        this.options = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            formatsToSupport: [
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.CODE_39
            ],
            ...options
        };
        
        this.init();
    }

    /**
     * Initialize the barcode scanner
     */
    init() {
        try {
            this.scanner = new Html5Qrcode(this.containerId);
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize barcode scanner:', error);
            this.showError('Failed to initialize barcode scanner. Please try refreshing the page.');
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
     * Start camera scanning
     */
    async startCamera() {
        if (this.isScanning) {
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

            // Start scanning
            await this.scanner.start(
                cameraId,
                this.options,
                (decodedText, decodedResult) => this.onScanSuccess(decodedText, decodedResult),
                (errorMessage) => this.onScanError(errorMessage)
            );

            this.isScanning = true;
            this.updateUI('scanning');
            this.hideLoading();

        } catch (error) {
            console.error('Camera start error:', error);
            this.handleCameraError(error);
        }
    }

    /**
     * Stop camera scanning
     */
    async stopCamera() {
        if (!this.isScanning) {
            return;
        }

        try {
            await this.scanner.stop();
            this.isScanning = false;
            this.updateUI('stopped');
        } catch (error) {
            console.error('Error stopping camera:', error);
        }
    }

    /**
     * Handle successful barcode scan
     */
    onScanSuccess(decodedText, decodedResult) {
        console.log('Barcode scanned:', decodedText);
        
        // Stop scanning to prevent multiple scans
        this.stopCamera();
        
        // Show processing indicator
        this.showLoading('Processing barcode...');
        
        // Send scanned result to server via htmx
        this.sendToServer(decodedText, 'camera');
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
     * Handle file selection for file-based scanning
     */
    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            this.showError('Please select a valid image file (JPEG, PNG, or WebP)');
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.showError('File size too large. Please select an image smaller than 10MB.');
            return;
        }

        try {
            this.showLoading('Processing image...');
            
            // Scan the file
            const decodedText = await this.scanner.scanFile(file, true);
            this.onScanSuccess(decodedText, null);
            
        } catch (error) {
            console.error('File scan error:', error);
            this.showError('Could not detect a barcode in this image. Please try a clearer image or use the camera.');
        }
    }

    /**
     * Send scanned barcode to server
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
        }).catch((error) => {
            console.error('Server communication error:', error);
            this.hideLoading();
            this.showError('Failed to process barcode. Please try again.');
        });
    }

    /**
     * Handle camera permission and initialization errors
     */
    handleCameraError(error) {
        this.hideLoading();
        
        let errorMessage = 'Camera access failed. ';
        let showFileOption = true;

        if (error.name === 'NotAllowedError' || error.message.includes('Permission denied')) {
            errorMessage += 'Please allow camera access and try again, or use the file upload option below.';
        } else if (error.name === 'NotFoundError' || error.message.includes('No cameras found')) {
            errorMessage += 'No camera found on this device. Please use the file upload option below.';
        } else if (error.name === 'NotSupportedError') {
            errorMessage += 'Camera not supported in this browser. Please use the file upload option below.';
        } else if (error.message.includes('HTTPS')) {
            errorMessage += 'Camera access requires a secure connection (HTTPS). Please use the file upload option below.';
        } else {
            errorMessage += 'Please try the file upload option below or enter the ISBN manually.';
        }

        this.showError(errorMessage, showFileOption);
        this.updateUI('error');
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
     * Cleanup scanner resources
     */
    destroy() {
        if (this.isScanning) {
            this.stopCamera();
        }
        this.scanner = null;
    }
}

// Initialize scanner when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the scanner page
    const scannerContainer = document.getElementById('barcode-reader');
    if (scannerContainer) {
        // Check if html5-qrcode library is loaded
        if (typeof Html5Qrcode === 'undefined') {
            console.error('html5-qrcode library not loaded');
            document.getElementById('error-message').style.display = 'block';
            document.getElementById('error-text').textContent = 'Barcode scanning library failed to load. Please refresh the page.';
            return;
        }

        // Initialize the scanner
        window.barcodeScanner = new BarcodeScanner('barcode-reader');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.barcodeScanner) {
        window.barcodeScanner.destroy();
    }
});