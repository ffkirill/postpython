# Postpython
Postpython is a library for [Postman](https://www.getpostman.com/) that run postman's collections.
If you are using postman, but collection runner is not flexible enough for you and postman codegen is too boring,
Postpython is here for your continuous integration.

## Why use Postpython instead of postman codegen?
- Postman codegen should be applied one by one for each request and it's boring when your api changes,
 but with postpython you don't need to generate code.
 Just export collection with postman and use it with Postpython.
- In code generation you don't have environment feature any more and variables are hardcoded.

## Why user Postpython instead of Postman collection runner?
- With postpython you write your own script. But collection runner just tun all your requests one by one.
So with Postpython you can design more complex test suites.

## How to use?

Import `PostPython`
```$python
from postpython.core import PostPython
```
Make an instance from `PostPython` and give address of postman collection file.
```$python
runner = PostPython('/path/to/collection/Postman echo.postman_collection')
```
Now you can call your request. Folders' name change to upper camel case and requests' name change to lowercase form.
In this example the name of folder is "Request Methods" and it's change to `RequestMethods` and the name of request was
"GET Request" and it's change to `get_request`. So you should call a function like `runner.YourFolderName.you_request_name()`
```$python
response = runner.RequestMethods.get_request()
print(response.json())
print(response.status_code)
```

### Variable assignment
In Postpython you can assign values to environment variables in runtime.
```
runner.environment.update({'BASE_URL': 'http://127.0.0.1:5000'})
runner.environment.update({'PASSWORD': 'test', 'EMAIL': 'you@email.com'})
```
