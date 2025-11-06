"""
Optional GPT-based report generation for enhanced violation descriptions
Only used if OPENAI_API_KEY environment variable is set
"""

import os

def generate_description(payload):
    """
    Generate enhanced violation description using OpenAI
    
    Args:
        payload (dict): Violation details including type, vehicle_no, timestamp
        
    Returns:
        str: Generated description or fallback template
    """
    # Check if OpenAI API key is available
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        print("OpenAI API key not found, using template description")
        return generate_template_description(payload)
    
    try:
        import openai
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Prepare prompt
        violation_type = payload.get('violation_type', 'Unknown')
        vehicle_no = payload.get('vehicle_no', 'Unknown')
        timestamp = payload.get('timestamp', 0)
        
        time_str = f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
        
        prompt = f"""Generate a professional traffic violation description for an e-challan.
        
Details:
- Vehicle Number: {vehicle_no}
- Violation Type: {violation_type}
- Time in video: {time_str}

Requirements:
- Keep it official and factual
- Maximum 2-3 sentences
- Include legal reference if applicable
- Professional tone suitable for official documentation
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a traffic enforcement officer writing official violation descriptions for e-challans."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        description = response.choices[0].message.content.strip()
        return description
        
    except ImportError:
        print("OpenAI library not available, using template description")
        return generate_template_description(payload)
    except Exception as e:
        print(f"Error generating GPT description: {e}")
        return generate_template_description(payload)

def generate_template_description(payload):
    """
    Generate template-based description
    
    Args:
        payload (dict): Violation details
        
    Returns:
        str: Template description
    """
    violation_type = payload.get('violation_type', 'Unknown')
    vehicle_no = payload.get('vehicle_no', 'Unknown')
    timestamp = payload.get('timestamp', 0)
    
    time_str = f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
    
    templates = {
        'NO_HELMET': f"Vehicle {vehicle_no} was observed being operated without the mandatory protective helmet at timestamp {time_str}. This violation contravenes Motor Vehicle Act safety regulations requiring all two-wheeler operators and passengers to wear ISI-marked helmets.",
        
        'TRIPLE_RIDING': f"Vehicle {vehicle_no} was found carrying more than the permitted number of passengers at timestamp {time_str}. This violation exceeds the legal limit of two persons on a two-wheeler as specified under traffic regulations.",
        
        'DEFAULT': f"Traffic safety violation detected for vehicle {vehicle_no} at timestamp {time_str}. The observed behavior contravenes established traffic safety regulations and poses risk to road users."
    }
    
    return templates.get(violation_type, templates['DEFAULT'])