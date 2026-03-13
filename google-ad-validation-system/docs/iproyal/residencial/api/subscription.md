# Subscription

## Get Subscription

<mark style="color:green;">`GET`</mark> `/residential/subscription`

#### Example request:

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/residential/subscription \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential/subscription';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPGET, true);
$headers = [
    "Authorization: Bearer $api_token"
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
url = 'https://resi-api.iproyal.com/v1/residential/subscription'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/residential/subscription';

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/residential/subscription";

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println(content.toString());
            } else {
                System.out.println("GET request failed. Response Code: " + responseCode);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken = "<your_api_token>"
	url    = "https://resi-api.iproyal.com/v1/residential/subscription"
)

func main() {
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)

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
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/residential/subscription";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

#### Example response:

```json
{
  "quantity": 1000,
  "amount": 3150,
  "status": "paid",
  "next_payment_date": "2025-07-26",
  "payment_method": "balance",
  "card_id": null
}
```

## Delete Subscription

<mark style="color:red;">`DELETE`</mark> `/residential/subscription`

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X DELETE https://resi-api.iproyal.com/v1/residential/subscription \
     -H "Authorization: Bearer <your_api_token>"
     -H "Content-Type: application/json" 
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential/subscription';

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'DELETE',
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ]
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
url = 'https://resi-api.iproyal.com/v1/residential/orders'

headers = {
    'Authorization': 'Bearer ' + api_token,
    'Content-Type': 'application/json'
}

response = requests.delete(url, headers=headers)

print(response.status_code)
if response.status_code == 204:
    print("Subscription deleted successfully")
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');
const apiToken = '<your_api_token>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: '/v1/residential/subscription',
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + apiToken,
    'Content-Type': 'application/json'
  }
};

const req = https.request(options, (res) => {
  console.log('Status Code:', res.statusCode);
  let responseData = '';
  res.on('data', (chunk) => {
    responseData += chunk;
  });
  res.on('end', () => {
    if (responseData) {
      console.log('Response:', responseData);
    } else {
      console.log('No response body');
    }
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

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
        String url = "https://resi-api.iproyal.com/v1/residential/subscription";

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiToken)
                .DELETE()
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println("Response Code: " + response.statusCode());
        System.out.println("Response Body: " + response.body());
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
    "encoding/json"
    "fmt"
    "io"
    "log"
    "net/http"
)

const (
    apiToken = "<your_api_token>"
    url      = "https://resi-api.iproyal.com/v1/residential/subscription"
)

func main() {
    req, err := http.NewRequest(http.MethodDelete, url, nil)
    if err != nil {
        log.Fatal("Error creating request:", err)
    }
    
    req.Header.Set("Authorization", "Bearer "+apiToken)
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        log.Fatal("Error making request:", err)
    }
    defer resp.Body.Close()
    
    fmt.Println("Status Code:", resp.StatusCode)
    
    responseBody, err := io.ReadAll(resp.Body)
    if err != nil {
        log.Fatal("Error reading response body:", err)
    }
    
    if len(responseBody) > 0 {
        var jsonResponse map[string]interface{}
        err = json.Unmarshal(responseBody, &jsonResponse)
        if err != nil {
            log.Fatal("Error unmarshaling JSON:", err)
        }
        fmt.Printf("%+v\n", jsonResponse)
    } else {
        fmt.Println("No response body")
    }
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/residential/subscription";
        
        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", "Bearer " + apiToken);
            HttpResponseMessage response = await client.DeleteAsync(url);
            Console.WriteLine((int)response.StatusCode);
            
            string responseText = await response.Content.ReadAsStringAsync();
            
            if (!string.IsNullOrEmpty(responseText))
            {
                var jsonResponse = JsonSerializer.Deserialize<JsonElement>(responseText);
                Console.WriteLine(jsonResponse);
            }
            else
            {
                Console.WriteLine("No response body");
            }
        }
    }
}
```

{% endtab %}
{% endtabs %}

## Change payment method

<mark style="color:blue;">`POST`</mark> `/residential/subscription/change-payment-method`

**Query Parameters:**

| Name            | Type    | Description                       |
| --------------- | ------- | --------------------------------- |
| payment\_method | String  | `balance` or `card`               |
| card\_id        | Integer | Card that is attached to the user |

#### Example request:

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <your_api_token>" \
     -d '{
           "payment_method": "card",
           "card_id": 1231
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method';

$data = [
    'payment_method' => 'card',
    'card_id' => 1231
];

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ],
    CURLOPT_POSTFIELDS => json_encode($data)
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
url = 'https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method';

data = {
    'payment_method': 'card',
    'card_id': 1231
}

headers = {
    'Authorization': 'Bearer ' + api_token,
    'Content-Type': 'application/json'
}

response = requests.post(url, json=data, headers=headers)

print(response.status_code)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';

const data = JSON.stringify({payment_method: 'balance'});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: '/v1/residential/subscription/change-payment-method',
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + apiToken,
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = https.request(options, (res) => {
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
        String accessToken = "<your_access_token>";
        String url = "https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method";

        String requestBody = """
            {
                "payment_method": "card",
                "card_id": 1231
            }
        """;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + accessToken)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println("Response Code: " + response.statusCode());
    }
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
    "log"
    "net/http"
)

const (
    apiToken = "<your_api_token>"
    url      = "https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method"
)

func main() {
    data := map[string]interface{}{
        "payment_method": "balance",
    }

    jsonData, err := json.Marshal(data)
    if err != nil {
        log.Fatal("Error marshaling JSON:", err)
    }

    req, err := http.NewRequest(http.MethodPost, url, bytes.NewBuffer(jsonData))
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

    fmt.Println("Status Code:", resp.StatusCode)
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/residential/subscription/change-payment-method";

        var data = new
        {
            payment_method = "card",
            card_id = 322
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", "Bearer " + apiToken);

            var jsonData = JsonSerializer.Serialize(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PostAsync(url, content);

            Console.WriteLine((int)response.StatusCode);
        }
    }
}
```

{% endtab %}
{% endtabs %}
