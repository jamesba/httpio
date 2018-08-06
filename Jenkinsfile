@Library("rd-apmm-groovy-ci-library@v1.x") _

/*
 Runs the following steps in parallel and reports results to GitHub:
 - Lint using flake8
 - Run Python 2.7 unit tests in tox
 - Run Pythin 3 unit tests in tox

 If these steps succeed and the master branch is being built, wheels are uploaded to Artifactory.

 Optionally you can set FORCE_PYUPLOAD to force upload to Artifactory.


 This file makes use of custom steps defined in a BBC internal library for use on our own Jenkins instances. As
 such it will not be immediately useable outside of a BBC environment, but may still serve as inspiration and an
 example of how to implement CI for this package.
*/

pipeline {
    agent {
        label "16.04&&ipstudio-deps"
    }
    options {
        ansiColor('xterm') // Add support for coloured output
        buildDiscarder(logRotator(numToKeepStr: '10')) // Discard old builds
    }
    parameters {
        booleanParam(name: "FORCE_PYUPLOAD", defaultValue: false, description: "Force Python artifact upload")
    }
    environment {
        http_proxy = "http://www-cache.rd.bbc.co.uk:8080"
        https_proxy = "http://www-cache.rd.bbc.co.uk:8080"
    }
    stages {
        stage ("Linting Check") {
            steps {
                script {
                    env.lint_result = "FAILURE"
                }
                //bbcGithubNotify(context: "lint/flake8", status: "PENDING")
                sh 'flake8'
                script {
                    env.lint_result = "SUCCESS" // This will only run if the sh above succeeded
                }
            }
            post {
                always {
                    //bbcGithubNotify(context: "lint/flake8", status: env.lint_result)
                }
            }
        }
        stage ("Python 2.7 Unit Tests") {
            steps {
                script {
                    env.py27_result = "FAILURE"
                }
                //bbcGithubNotify(context: "tests/py27", status: "PENDING")
                // Use a workdirectory in /tmp to avoid shebang length limitation
                sh 'tox -e py27 --recreate --workdir /tmp/$(basename ${WORKSPACE})/tox-py27'
                script {
                    env.py27_result = "SUCCESS" // This will only run if the sh above succeeded
                }
            }
            post {
                always {
                    //bbcGithubNotify(context: "tests/py27", status: env.py27_result)
                }
            }
        }
        stage ("Python 3 Unit Tests") {
            steps {
                script {
                    env.py3_result = "FAILURE"
                }
                //bbcGithubNotify(context: "tests/py3", status: "PENDING")
                // Use a workdirectory in /tmp to avoid shebang length limitation
                sh 'tox -e py3 --recreate --workdir /tmp/$(basename ${WORKSPACE})/tox-py3'
                script {
                    env.py3_result = "SUCCESS" // This will only run if the sh above succeeded
                }
            }
            post {
                always {
                    //bbcGithubNotify(context: "tests/py3", status: env.py3_result)
                }
            }
        }
        stage ("Upload to Artifactory") {
            when {
                anyOf {
                    expression { return params.FORCE_PYUPLOAD }
                    expression {
                        bbcShouldUploadArtifacts(branches: ["master"])
                    }
                }
            }
            steps {
                script {
                    env.artifactoryUpload_result = "FAILURE"
                }
                //bbcGithubNotify(context: "artifactory/upload", status: "PENDING")
                sh 'rm -rf dist/*'
                bbcMakeWheel("py27")
                bbcMakeWheel("py3")
                bbcTwineUpload(toxenv: "py3")
                script {
                    env.artifactoryUpload_result = "SUCCESS" // This will only run if the steps above succeeded
                }
            }
            post {
                always {
                    //bbcGithubNotify(context: "artifactory/upload", status: env.artifactoryUpload_result)
                }
            }
        }
    }
    post {
        always {
            bbcSlackNotify()
        }
    }
}
