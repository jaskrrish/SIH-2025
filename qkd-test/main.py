import base64
from etsi_qkd_014_client import QKD014Client

client_alice = QKD014Client(
    "192.168.10.101",
    "clientCert.pem",
    "clientKey.pem",
    "rootCA.pem",
    force_insecure=True
)

try:
    code, data = client_alice.get_key("SAEBOB")  
    print(code)  # 200

    print(data)


    if code == 200:
        key_id = data.keys[0].key_id
        key_alice = data.keys[0].key

        print(key_alice == key_alice)  # True

        print(key_alice) 
        print(f"".join(["{:08b}".format(x) for x in base64.b64decode(key_alice)]))

except Exception as e:
    print(f"No real KME server available. Using simulator...\n")
    
    # Simulate with BB84
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'qutemail-backend'))
    from apps.qkd.simulator import BB84Simulator
    
    simulator = BB84Simulator(error_rate=0.0)
    
    # Generate quantum key
    alice_key_obj, _ = simulator.generate_key_pair(key_size=256)
    
    code = 200
    key_id = alice_key_obj.key_id
    key_alice = base64.b64encode(alice_key_obj.key_material).decode('utf-8')
    
    print(code)  # 200
    
    print(f"Key id : {key_id}")
    print(f"Key : {key_alice}")
    
    print(True)  # True
    
    print(key_alice)  
    print(f"".join(["{:08b}".format(x) for x in base64.b64decode(key_alice)]))