# pyAnsys_DPF_dash

See [Medium article](https://towardsdatascience.com/ansys-in-a-python-web-app-part-1-post-processing-with-pydpf-44d2fbaa6135)

![](img/pyAnsys_DPF.GIF)

## Updated Commit (ansys_customIP): Add Custom IP 

- If there is a need to specify a custom IP which can be used to host the web app so that it can be accessed externally within the network. Specify the `--ip` flag along with the address of the server. For example:

  ```bash
python pyAnsys_DPF_dash.py --ip 0.0.0.0
  ```

- Note, that you should have permissions to run the app on that IP address. i.e., it needs to be made public within the organization.

  

