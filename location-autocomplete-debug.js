/**
 * Debug version of location autocomplete with enhanced logging
 */

// Debug function to check if elements are properly positioned
function debugDropdownPosition() {
    const countryInputs = document.querySelectorAll('input[name="country"]');
    const cityInputs = document.querySelectorAll('input[name="city"]');
    
    console.log('Country inputs found:', countryInputs.length);
    console.log('City inputs found:', cityInputs.length);
    
    countryInputs.forEach((input, index) => {
        console.log(`Country input ${index}:`, {
            parentNode: input.parentNode.className,
            hasWrapper: input.parentNode.className.includes('location-autocomplete-wrapper'),
            position: window.getComputedStyle(input.parentNode).position
        });
    });
}

// Enhanced initialization with debug logging
function initializeLocationAutocompleteDebug() {
    console.log('Initializing location autocomplete with debug...');
    
    const countryInputs = document.querySelectorAll('input[name="country"]');
    const cityInputs = document.querySelectorAll('input[name="city"]');
    
    console.log('Found', countryInputs.length, 'country inputs');
    console.log('Found', cityInputs.length, 'city inputs');
    
    // Initialize country autocomplete
    countryInputs.forEach((input, index) => {
        console.log(`Setting up country input ${index}`);
        setupCountryAutocomplete(input);
    });
    
    // Initialize city autocomplete
    cityInputs.forEach((input, index) => {
        console.log(`Setting up city input ${index}`);
        setupCityAutocomplete(input);
    });
}

function setupCountryAutocomplete(input) {
    console.log('Setting up country autocomplete for:', input);
    
    // Create wrapper if it doesn't exist
    if (!input.parentNode.classList.contains('location-autocomplete-wrapper')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'location-autocomplete-wrapper';
        wrapper.style.cssText = 'position: relative; width: 100%; overflow: visible;';
        
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        
        console.log('Created wrapper for country input');
    }
    
    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'autocomplete-dropdown country-dropdown';
    dropdown.style.cssText = `
        position: fixed;
        background: white;
        border: 1px solid #dee2e6;
        border-top: none;
        border-radius: 0 0 0.375rem 0.375rem;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        max-height: 200px;
        overflow-y: auto;
        z-index: 10000;
        display: none;
        min-width: 200px;
    `;
    
    input.parentNode.appendChild(dropdown);
    
    input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        console.log('Country input changed:', query);
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }
        
        // Sample countries for testing
        const countries = [
            'United States', 'India', 'United Kingdom', 'Germany', 'Canada', 
            'Australia', 'France', 'Italy', 'Spain', 'Netherlands', 'Sweden',
            'Norway', 'Denmark', 'Finland', 'Switzerland', 'Austria', 'Belgium',
            'Argentina', 'Brazil', 'Mexico', 'Chile', 'Colombia', 'Peru'
        ];
        
        const matches = countries.filter(country => 
            country.toLowerCase().includes(query)
        ).slice(0, 10);
        
        console.log('Country matches:', matches);
        showDropdownWithDebug(dropdown, matches, input, 'country');
    });
    
    // Position dropdown relative to input when shown
    input.addEventListener('focus', function() {
        positionDropdown(dropdown, input);
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function setupCityAutocomplete(input) {
    console.log('Setting up city autocomplete for:', input);
    
    // Create wrapper if it doesn't exist
    if (!input.parentNode.classList.contains('location-autocomplete-wrapper')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'location-autocomplete-wrapper';
        wrapper.style.cssText = 'position: relative; width: 100%; overflow: visible;';
        
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        
        console.log('Created wrapper for city input');
    }
    
    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'autocomplete-dropdown city-dropdown';
    dropdown.style.cssText = `
        position: fixed;
        background: white;
        border: 1px solid #dee2e6;
        border-top: none;
        border-radius: 0 0 0.375rem 0.375rem;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        max-height: 200px;
        overflow-y: auto;
        z-index: 10000;
        display: none;
        min-width: 200px;
    `;
    
    input.parentNode.appendChild(dropdown);
    
    input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        console.log('City input changed:', query);
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }
        
        // Sample cities for testing
        const cities = [
            'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
            'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
            'San Francisco', 'Columbus', 'Charlotte', 'Fort Worth', 'Detroit', 'Seattle',
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune',
            'London', 'Manchester', 'Birmingham', 'Liverpool', 'Leeds', 'Sheffield',
            'Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Stuttgart', 'Düsseldorf',
            'Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Edmonton', 'Ottawa'
        ];
        
        const matches = cities.filter(city => 
            city.toLowerCase().includes(query)
        ).slice(0, 10);
        
        console.log('City matches:', matches);
        showDropdownWithDebug(dropdown, matches, input, 'city');
    });
    
    // Position dropdown relative to input when shown
    input.addEventListener('focus', function() {
        positionDropdown(dropdown, input);
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function positionDropdown(dropdown, input) {
    const rect = input.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
    
    dropdown.style.top = (rect.bottom + scrollTop) + 'px';
    dropdown.style.left = (rect.left + scrollLeft) + 'px';
    dropdown.style.width = rect.width + 'px';
    
    console.log('Positioned dropdown at:', {
        top: dropdown.style.top,
        left: dropdown.style.left,
        width: dropdown.style.width
    });
}

function showDropdownWithDebug(dropdown, matches, input, type) {
    console.log(`Showing ${type} dropdown with ${matches.length} matches`);
    
    dropdown.innerHTML = '';
    
    if (matches.length === 0) {
        dropdown.style.display = 'none';
        return;
    }
    
    matches.forEach(match => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = match;
        item.style.cssText = `
            padding: 0.75rem;
            cursor: pointer;
            border-bottom: 1px solid #f8f9fa;
            transition: background-color 0.15s ease-in-out;
            font-size: 0.875rem;
            color: #495057;
        `;
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
            this.style.color = '#212529';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.color = '#495057';
        });
        
        item.addEventListener('click', function() {
            console.log(`Selected ${type}:`, match);
            input.value = match;
            dropdown.style.display = 'none';
        });
        
        dropdown.appendChild(item);
    });
    
    // Position dropdown relative to input field
    positionDropdown(dropdown, input);
    
    dropdown.style.display = 'block';
    console.log('Dropdown displayed and positioned');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing location autocomplete...');
    setTimeout(initializeLocationAutocompleteDebug, 100);
    setTimeout(debugDropdownPosition, 200);
});

// Export for testing
window.locationAutocompleteDebug = {
    initialize: initializeLocationAutocompleteDebug,
    debug: debugDropdownPosition
};