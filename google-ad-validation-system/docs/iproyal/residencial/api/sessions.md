# Sessions

### Remove Sessions <a href="#remove-sessions" id="remove-sessions"></a>

<mark style="color:red;">`DELETE`</mark> `/sessions`

**Body Parameters**

| Name                      | Type  | Description                            |
| ------------------------- | ----- | -------------------------------------- |
| residential\_user\_hashes | Array | Array of user hashes to reset sessions |

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X DELETE https://resi-api.iproyal.com/v1/sessions \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{"residential_user_hashes":["hash1","hash2","hash3"]}'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/sessions';
$residential_user_hashes = ['hash1', 'hash2', 'hash3'];
$data = json_encode(['residential_user_hashes' => $residential_user_hashes]);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "DELETE");
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
$headers = [
    "Authorization: Bearer $api_token",
    "Content-Type: application/json"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/sessions'
residential_user_hashes = ['hash1', 'hash2', 'hash3']
data = {'residential_user_hashes': residential_user_hashes}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.delete(url, headers=headers, json=data)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/sessions';
const residentialUserHashes = ['hash1', 'hash2', 'hash3'];
const data = JSON.stringify({ residential_user_hashes: residentialUserHashes });

const options = {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${apiToken}`,
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = https.request(url, options, (res) => {
  let responseData = '';

  res.on('data', (chunk) => {
    responseData += chunk;
  });

  res.on('end', () => {
    console.log(responseData);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.write(data);
req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class Main {
    public static void main(String[] args) throws Exception {
        String apiToken = "<your_api_token>";
        String url = "https://resi-api.iproyal.com/v1/sessions";

        String requestBody = "{\"residential_user_hashes\": [\"hash1\", \"hash2\", \"hash3\"]}";

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Authorization", "Bearer " + apiToken)
                .header("Content-Type", "application/json")
                .header("X-HTTP-Method-Override", "DELETE")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println(response);
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken = "<your_api_token>"
	sessionsURL = "https://resi-api.iproyal.com/v1/sessions"
)

func main() {
	data := map[string]interface{}{
		"residential_user_hashes": []string{"hash1", "hash2", "hash3"},
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal("Error marshaling JSON:", err)
	}

	req, err := http.NewRequest(http.MethodDelete, sessionsURL, bytes.NewBuffer(jsonData))
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}
	
	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/sessions";
        string[] residentialUserHashes = { "hash1", "hash2", "hash3" };

        var data = new
        {
            residential_user_hashes = residentialUserHashes
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");
            client.DefaultRequestHeaders.Add("Content-Type", "application/json");

            var jsonData = JsonConvert.SerializeObject(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.DeleteAsync(url, content);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}
