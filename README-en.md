**MCJ-CloudHub**

[日本語版 README はこちら](https://github.com/nii-gakunin-cloud/mcj-cloudhub/blob/main/README.md)

**What is MCJ-CloudHub?**

MCJ-CloudHub is a web-based programming assignment platform that supports simultaneous and collaborative use across multiple courses. It uses [<span class="underline">JupyterHub</span>](https://github.com/jupyterhub/jupyterhub) for providing notebook-based environments and [<span class="underline">nbgrader</span>](https://github.com/jupyter/nbgrader) for distributing, collecting, and grading assignments. The system includes custom modifications and configurations to support multi-course operation.

This repository provides an application template for deploying MCJ-CloudHub on the [<span class="underline">GakuNin Cloud On-Demand Construction Service (OCS)</span>](https://cloud.gakunin.jp/ocs/).

**Usage Workflow**

  - **Login to JupyterHub via LMS with LTI Authentication**  
    Users log in through an LMS (e.g., Moodle) using LTI-based authentication. Each LMS course includes a login link to the corresponding JupyterHub environment.

  - **Course-specific Jupyter Notebook Environment in Docker Containers**  
    Upon login, a Docker container is launched with environment settings specific to the selected course. Only the selected course will be available in nbgrader, preventing accidental course selection.

  - **Assignment Interaction via nbgrader**  
    Instructors and students interact with assignments through nbgrader's interface.

**Customization of JupyterHub and nbgrader**

MCJ-CloudHub is designed with the following goals:

  - **Simultaneous use of Jupyter + nbgrader in multiple courses**  
    The system automatically generates necessary directories and configuration files for each course.

  - **Minimal post-deployment maintenance**  
    Instructors do not need to manually configure the environment. All course-specific setup is automated, making it easy to maintain even across multiple courses.

**Key Features:**

  - **Automatic directory creation**  
    Per-course directories are created with a custom layout and permission settings, enabling safe concurrent access.

  - **Auto-generation of config files**  
    Both jupyterhub\_config.py and nbgrader\_config.py are automatically generated per user at login.

  - **JST support for nbgrader**  
    The system customizes nbgrader to allow instructors to set and view assignment deadlines in Japan Standard Time (JST), eliminating the need to manually specify time zone offsets.

**JupyterHub User Authentication**

MCJ-CloudHub uses **LTI 1.3** for user authentication with supported LMS platforms. Setup guides are included in the template.

  - **Verified LMS Platforms and Recommended Versions**:
    
      - **Moodle** (version 4.x.x recommended due to simpler setup)
        
          - 3.9.9
        
          - 4.0.6 (recommended)
        
          - 4.2.7 (recommended)

**System Architecture**

A diagram showing the overall architecture is available in the repository:

![](images/arch-readme.png)

**Notes on nbgrader Modifications**

Due to the customized directory structure and JST support, some standard nbgrader features are disabled:

  - nbgrader quickstart is disabled  
    The generated directories and files from quickstart do not align with MCJ-CloudHub’s structure.

  - Time zone setting is fixed to JST  
    The system is not designed to support other time zones.

**Deployment on OCS**

In OCS, containers are deployed in a Docker-in-Docker configuration.

  - **VC Nodes (Base Containers):**
    
      - **Manager:**  
        Hosts JupyterHub, MariaDB, and other system containers  
        Functions as a Docker Swarm manager and NFS server  
        Only one manager node is used
    
      - **Worker:**  
        Runs each user's single-user Jupyter notebook servers  
        Functions as Docker Swarm worker nodes  
        Multiple worker nodes can be launched based on usage
